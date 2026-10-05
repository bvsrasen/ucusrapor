"""Uçuş kayıtlarını ortak bir tabloya çeviren fonksiyonlar.

Ortak tablo sütunları:
    t_s        kaydın başından geçen süre (s)
    basinc_pa  barometrik basınç (Pa)
    ivme_g     roketin ekseni boyunca ivme (g); rampada +1 g okur, motor
               yanarken artar, motor bitince hava direnci yüzünden negatife
               düşer.
    ncsu_durum NCSU uçuş yazılımının o anki durumu (S, M, C, F, L); sadece
               NCSU kayıtlarında var.
"""
import numpy as np
import pandas as pd

HZ = 50.0  # algoritmalar örnek sayısıyla çalıştığı için bütün kayıtlar bu hıza getiriliyor


def oku_ncsu_imu(yol):
    """NCSU'nun Parker-LORD 3DM-CX5 kayıtları: zaman ns, basınç mbar, ivme g.

    Dosyada ham ve tahmin paketleri karışık; sadece basınç içeren satırlar alınıyor.
    """
    d = pd.read_csv(yol, usecols=["state_letter", "timestamp", "scaledAmbientPressure",
                                  "scaledAccelX", "scaledAccelY", "scaledAccelZ"])
    d = d.dropna(subset=["scaledAmbientPressure", "scaledAccelX"])
    return _ortak(d["timestamp"] / 1e9, d["scaledAmbientPressure"] * 100.0,
                  d[["scaledAccelX", "scaledAccelY", "scaledAccelZ"]], d["state_letter"])


def oku_firm(yol):
    """NCSU'nun FIRM kartı kayıtları: zaman s, basınç Pa, ivme g."""
    d = pd.read_csv(yol, usecols=["state_letter", "timestamp_seconds", "pressure_pascals",
                                  "raw_acceleration_x_gs", "raw_acceleration_y_gs", "raw_acceleration_z_gs"])
    d = d.dropna(subset=["pressure_pascals", "raw_acceleration_x_gs"])
    return _ortak(d["timestamp_seconds"], d["pressure_pascals"],
                  d[["raw_acceleration_x_gs", "raw_acceleration_y_gs", "raw_acceleration_z_gs"]],
                  d["state_letter"])


def _ortak(t, basinc, ivme3, durum):
    d = pd.DataFrame({"t_s": t.to_numpy(dtype=float), "basinc_pa": basinc.to_numpy(dtype=float),
                      "ncsu_durum": durum.to_numpy()})
    a = ivme3.to_numpy(dtype=float)
    # Birkaç kayıtta satırlar zaman sırasında değil
    sira = np.argsort(d["t_s"].to_numpy(), kind="stable")
    d, a = d.iloc[sira].reset_index(drop=True), a[sira]
    d["t_s"] -= d["t_s"].iloc[0]
    # Kartlar rokete farklı yönlerde monte edilmiş. Rampada roket dik durduğu
    # için ilk 2 s'de ölçülen yerçekimi yönü roketin ekseni; ivmeyi bu eksene izdüşürüyoruz.
    eksen = a[d["t_s"].to_numpy() < 2.0].mean(axis=0)
    d.insert(2, "ivme_g", a @ (eksen / np.linalg.norm(eksen)))
    return d


def oku_kayit(yol):
    """Kendi uçuş bilgisayarınızın kaydı: en az t_s, basinc_pa, ivme_g sütunları."""
    d = pd.read_csv(yol)
    eksik = {"t_s", "basinc_pa", "ivme_g"} - set(d.columns)
    if eksik:
        raise ValueError(f"{yol}: eksik sütun {sorted(eksik)}")
    # Zamanı olmayan satır sıralanamaz ve yeniden örneklemeyi bozar
    d = d.dropna(subset=["t_s"])
    return d.sort_values("t_s", kind="stable").reset_index(drop=True)


def yeniden_ornekle(d, hz=HZ):
    """Kaydı sabit hızlı bir zaman çizelgesine getirir.

    Her an için o ana kadar gelen son örnek alınıyor; uçuş bilgisayarı da
    sensörü okuduğu anda en son ölçümü görür.
    """
    t = d["t_s"].to_numpy()
    izgara = t[0] + np.arange(0, np.floor((t[-1] - t[0]) * hz) + 1) / hz
    i = np.searchsorted(t, izgara, side="right") - 1
    yeni = d.iloc[i].reset_index(drop=True)
    yeni["t_s"] = np.round(izgara, 4)
    return yeni


def irtifa(basinc_pa, p0_pa):
    """Standart atmosfer modeliyle rampaya göre irtifa (m)."""
    return 44330.0 * (1.0 - (np.asarray(basinc_pa, dtype=float) / p0_pa) ** 0.190263)
