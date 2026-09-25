"""
UçuşRapor - Veri doğrulama, temizleme ve metrik hesaplama modülü.

Gereksinim karşılıkları (bkz. Confluence > 03 - Gereksinim Dokümanı):
    FR-01  CSV okuma                       -> veri_oku()
    FR-02  Eksik değer tespiti             -> temizle() / adım 3
    FR-03  Duplike satır temizleme         -> temizle() / adım 1
    FR-04  Aykırı değer (sıçrama) tespiti  -> temizle() / adım 4
    FR-05  Uçuş metrikleri                 -> metrikleri_hesapla()
"""

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

BEKLENEN_SUTUNLAR = [
    "zaman_ms", "irtifa_m", "basinc_hPa",
    "ivme_x_g", "ivme_y_g", "ivme_z_g", "sicaklik_C", "durum",
]
SENSOR_SUTUNLARI = ["irtifa_m", "basinc_hPa", "ivme_x_g", "ivme_y_g", "ivme_z_g", "sicaklik_C"]

DURUM_ADLARI = {
    0: "Rampada Bekleme",
    1: "Kalkış",
    2: "Motor Yanması",
    3: "Süzülme",
    4: "Apogee",
    5: "Sürüklenme Paraşütü",
    6: "Ana Paraşüt",
    7: "İniş",
}

# Fiziksel sınırlar: bu aralığın dışındaki değer sensör hatasıdır
FIZIKSEL_SINIRLAR = {
    "irtifa_m": (-50.0, 6000.0),
    "basinc_hPa": (300.0, 1100.0),
    "ivme_x_g": (-30.0, 30.0),
    "ivme_y_g": (-30.0, 30.0),
    "ivme_z_g": (-30.0, 30.0),
    "sicaklik_C": (-40.0, 70.0),
}

# Sıçrama tespiti: kayan medyandan bu kadar sapan tekil değer aykırıdır.
# 10 Hz'de roket bir örnekte en fazla ~35 m yol alır; 5 örneklik medyan
# penceresi için 200 m güvenli bir eşiktir.
SICRAMA_ESIKLERI = {
    "irtifa_m": 200.0,
    "basinc_hPa": 25.0,
    "ivme_z_g": 15.0,
}


class VeriFormatHatasi(Exception):
    """Girdi dosyası beklenen log formatında değilse fırlatılır."""


@dataclass
class TemizlemeSonucu:
    temiz: pd.DataFrame
    ham_satir_sayisi: int
    kayitlar: list = field(default_factory=list)  # veri kalitesi günlüğü

    def ozet(self):
        """Sorun tipine göre sayılar."""
        sayim = {}
        for k in self.kayitlar:
            sayim[k["tip"]] = sayim.get(k["tip"], 0) + 1
        return sayim


def veri_oku(dosya_yolu):
    """FR-01: Ham CSV log dosyasını okur ve formatını doğrular."""
    dosya_yolu = Path(dosya_yolu)
    if not dosya_yolu.exists():
        raise FileNotFoundError(f"Log dosyası bulunamadı: {dosya_yolu}")

    df = pd.read_csv(dosya_yolu)
    eksik = [s for s in BEKLENEN_SUTUNLAR if s not in df.columns]
    if eksik:
        raise VeriFormatHatasi(f"Log dosyasında eksik sütun(lar): {', '.join(eksik)}")
    if df.empty:
        raise VeriFormatHatasi("Log dosyası boş.")

    df = df[BEKLENEN_SUTUNLAR].copy()
    df.insert(0, "kaynak_satir", np.arange(2, len(df) + 2))  # CSV'deki satır no (başlık = 1)
    return df


def _kayit(kayitlar, satir, tip, sutun, deger, islem):
    kayitlar.append({
        "kaynak_satir": int(satir["kaynak_satir"]),
        "zaman_ms": int(satir["zaman_ms"]),
        "tip": tip,
        "sutun": sutun,
        "orijinal_deger": "" if pd.isna(deger) else deger,
        "islem": islem,
    })


def temizle(df):
    """Ham veriyi doğrular ve temizler. Her müdahale veri kalitesi günlüğüne yazılır."""
    ham_n = len(df)
    kayitlar = []
    df = df.copy()

    # 1) FR-03: Duplike satırlar (kaynak_satir hariç tüm sütunlar aynı)
    duplike_maske = df.duplicated(subset=BEKLENEN_SUTUNLAR, keep="first")
    for _, satir in df[duplike_maske].iterrows():
        _kayit(kayitlar, satir, "DUPLIKE_SATIR", "-", "", "Satır silindi")
    df = df[~duplike_maske]

    # 2) Geçersiz FSM durum kodu
    gecersiz = ~df["durum"].isin(DURUM_ADLARI.keys())
    for _, satir in df[gecersiz].iterrows():
        _kayit(kayitlar, satir, "GECERSIZ_DURUM", "durum", int(satir["durum"]), "Satır silindi")
    df = df[~gecersiz]

    df = df.sort_values("zaman_ms").reset_index(drop=True)

    # 3) FR-02: Eksik değerler
    for sutun in SENSOR_SUTUNLARI:
        for _, satir in df[df[sutun].isna()].iterrows():
            _kayit(kayitlar, satir, "EKSIK_DEGER", sutun, "", "Doğrusal interpolasyon ile dolduruldu")

    # 4) FR-04: Aykırı değerler (fiziksel sınır dışı veya kayan medyandan ani sapma)
    for sutun in SENSOR_SUTUNLARI:
        alt, ust = FIZIKSEL_SINIRLAR[sutun]
        seri = df[sutun]
        sinir_disi = (seri < alt) | (seri > ust)

        sicrama = pd.Series(False, index=df.index)
        if sutun in SICRAMA_ESIKLERI:
            medyan = seri.rolling(5, center=True, min_periods=3).median()
            sicrama = (seri - medyan).abs() > SICRAMA_ESIKLERI[sutun]

        aykiri = (sinir_disi | sicrama) & seri.notna()
        for idx, satir in df[aykiri].iterrows():
            _kayit(kayitlar, satir, "SENSOR_SICRAMASI", sutun, satir[sutun],
                   "Değer geçersiz sayıldı, interpolasyon ile düzeltildi")
        df.loc[aykiri, sutun] = np.nan

    # 5) Eksik ve geçersiz sayılan değerleri zamana göre doğrusal interpolasyonla doldur
    df = df.set_index("zaman_ms")
    df[SENSOR_SUTUNLARI] = df[SENSOR_SUTUNLARI].interpolate(method="index", limit_direction="both")
    df = df.reset_index()

    kayitlar.sort(key=lambda k: (k["zaman_ms"], k["tip"]))
    return TemizlemeSonucu(temiz=df, ham_satir_sayisi=ham_n, kayitlar=kayitlar)


def zenginlestir(df):
    """Rapor için türetilmiş sütunları ekler."""
    df = df.copy()
    kalkis_ms = df.loc[df["durum"] >= 1, "zaman_ms"].min()
    df["ucus_zamani_s"] = (df["zaman_ms"] - kalkis_ms) / 1000.0
    df["toplam_ivme_g"] = np.sqrt(df["ivme_x_g"] ** 2 + df["ivme_y_g"] ** 2 + df["ivme_z_g"] ** 2)
    df["durum_adi"] = df["durum"].map(DURUM_ADLARI)
    return df


def _ilk_zaman(df, durum):
    satirlar = df[df["durum"] == durum]
    return float(satirlar["ucus_zamani_s"].iloc[0]) if len(satirlar) else float("nan")


def _inis_hizi(df, durum):
    """Belirli bir aşamadaki ortalama iniş hızı (irtifa-zaman doğrusunun eğimi, m/s)."""
    faz = df[df["durum"] == durum]
    # Paraşüt açılışının ilk 3 saniyesindeki geçiş rejimi hariç tutulur
    faz = faz[faz["ucus_zamani_s"] >= faz["ucus_zamani_s"].min() + 3.0]
    if len(faz) < 5:
        return float("nan"), None
    egim = np.polyfit(faz["ucus_zamani_s"], faz["irtifa_m"], 1)[0]
    return float(-egim), (int(faz.index.min()), int(faz.index.max()))


def metrikleri_hesapla(df):
    """FR-05: Temel uçuş metriklerini hesaplar. `df` zenginleştirilmiş temiz veridir."""
    tepe_idx = df["irtifa_m"].idxmax()
    ivme_idx = df["toplam_ivme_g"].idxmax()
    suruklenme_hizi, suruklenme_aralik = _inis_hizi(df, 5)
    ana_hizi, ana_aralik = _inis_hizi(df, 6)

    return {
        "maks_irtifa_m": float(df.loc[tepe_idx, "irtifa_m"]),
        "apogee_zamani_s": float(df.loc[tepe_idx, "ucus_zamani_s"]),
        "maks_ivme_g": float(df.loc[ivme_idx, "toplam_ivme_g"]),
        "maks_ivme_zamani_s": float(df.loc[ivme_idx, "ucus_zamani_s"]),
        # Yanma süresi: kalkıştan süzülme aşamasının başlangıcına kadar geçen süre
        "yanma_suresi_s": _ilk_zaman(df, 3) - _ilk_zaman(df, 1),
        "suruklenme_parasutu_s": _ilk_zaman(df, 5),
        "ana_parasut_s": _ilk_zaman(df, 6),
        "ana_parasut_irtifa_m": float(df.loc[df["durum"] == 6, "irtifa_m"].iloc[0]),
        "inis_zamani_s": _ilk_zaman(df, 7),
        "ucus_suresi_s": _ilk_zaman(df, 7),  # kalkış t=0 kabul edilir
        "suruklenme_inis_hizi_ms": suruklenme_hizi,
        "ana_parasut_inis_hizi_ms": ana_hizi,
        "_suruklenme_aralik": suruklenme_aralik,  # rapordaki formüller için satır aralıkları
        "_ana_aralik": ana_aralik,
    }
