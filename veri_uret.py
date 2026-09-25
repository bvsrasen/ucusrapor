"""
UçuşRapor - Simüle Uçuş Verisi Üretici
=====================================

AKANA orta irtifa roketinin uçuş profiline dayalı, STM32 aviyonik kartının
SD karta yazdığı log formatında (CSV) simüle bir uçuş kaydı üretir.

Veri temizleme adımını test edebilmek için kayda BİLEREK hatalar eklenir:
  - Eksik değerler (boş hücreler)
  - Tekrar eden (duplike) satırlar
  - Sensör sıçramaları (fiziksel olarak imkânsız ani değerler)
  - Geçersiz FSM durum kodu

Eklenen her hata `veri/beklenen_hatalar.json` dosyasına yazılır; testler
temizleme modülünün bunları gerçekten yakaladığını bu dosyayla doğrular.

Kullanım:
    python veri_uret.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Simülasyon parametreleri (AKANA orta irtifa sınıfı roket için yaklaşık değerler)
# ---------------------------------------------------------------------------
TOHUM = 2026                # Aynı veriyi her seferinde üretmek için sabit rastgelelik tohumu
DT = 0.1                    # Örnekleme aralığı (s) -> 10 Hz kayıt
RAMPA_SURESI = 3.0          # Kalkış öncesi rampada bekleme (s)
YANMA_SURESI = 3.2          # Motor yanma süresi (s)
ITKI = 1450.0               # Ortalama motor itkisi (N)
KUTLE_DOLU = 13.0           # Kalkış kütlesi (kg)
KUTLE_BOS = 11.2            # Yakıt bittikten sonraki kütle (kg)
CD_A = 0.0072               # Sürükleme katsayısı x kesit alanı (m^2)
G = 9.80665                 # Yerçekimi ivmesi (m/s^2)
ANA_PARASUT_IRTIFA = 600.0  # Ana paraşütün açıldığı irtifa (m)
SURUKLENME_HIZI = 24.0      # Sürüklenme paraşütü ile iniş hızı (m/s)
ANA_PARASUT_HIZI = 6.5      # Ana paraşüt ile iniş hızı (m/s)
YER_BASINCI = 905.0         # Atış alanı zemin basıncı (hPa) ~ 1000 m rakım
YER_SICAKLIGI = 19.0        # Zemin sıcaklığı (°C)

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


def hava_yogunlugu(h):
    """Basit üstel atmosfer modeli ile hava yoğunluğu (kg/m^3)."""
    return 1.10 * np.exp(-h / 8500.0)


def basinc_hesapla(h):
    """Barometrik formül ile zeminden h metre yukarıdaki basınç (hPa)."""
    return YER_BASINCI * (1 - 2.25577e-5 * h) ** 5.25588


def ucus_simule_et():
    """Temiz (hatasız) uçuş verisini üretir ve DataFrame olarak döndürür."""
    rng = np.random.default_rng(TOHUM)
    kayitlar = []

    t, h, v = 0.0, 0.0, 0.0
    durum = 0
    apogee_sayac = 0
    inis_sayac = 0

    while True:
        # --- Durum makinesi geçişleri (STM32 üzerindeki FSM'nin mantığı) ---
        ucus_t = t - RAMPA_SURESI  # ateşlemeden itibaren geçen süre
        if durum == 0 and ucus_t >= 0:
            durum = 1
        elif durum == 1 and ucus_t >= 0.5:
            durum = 2
        elif durum == 2 and ucus_t >= YANMA_SURESI:
            durum = 3
        elif durum == 3 and v <= 0:
            durum = 4
        elif durum == 4:
            apogee_sayac += 1
            if apogee_sayac >= 5:           # apogee 0.5 s boyunca raporlanır
                durum = 5
        elif durum == 5 and h <= ANA_PARASUT_IRTIFA:
            durum = 6
        elif durum == 6 and h <= 0.5:
            durum = 7

        # --- Fizik: itki, sürükleme, yerçekimi ---
        if durum in (1, 2):
            kutle = KUTLE_DOLU - (KUTLE_DOLU - KUTLE_BOS) * min(ucus_t / YANMA_SURESI, 1)
            itki = ITKI
        else:
            kutle = KUTLE_BOS
            itki = 0.0

        if durum in (0, 7):
            a = 0.0
            v = 0.0
            ozgul_kuvvet = G  # rampada/yerde ivmeölçer +1 g okur
        elif durum in (5, 6):
            hedef_hiz = -SURUKLENME_HIZI if durum == 5 else -ANA_PARASUT_HIZI
            # Paraşüt altında hız hedef iniş hızına yaklaşır
            v += (hedef_hiz - v) * 0.35
            a = 0.0
            ozgul_kuvvet = G + rng.normal(0, 0.8)
        else:
            surukleme = 0.5 * hava_yogunlugu(h) * CD_A * v * abs(v)
            a = (itki - surukleme) / kutle - G
            v += a * DT
            ozgul_kuvvet = a + G  # ivmeölçer yerçekimini hissetmez

        h = max(h + v * DT, 0.0)
        if durum == 7:
            h = 0.0

        kayitlar.append({
            "zaman_ms": int(round(t * 1000)),
            "irtifa_m": round(h + rng.normal(0, 0.6), 2),
            "basinc_hPa": round(basinc_hesapla(h) + rng.normal(0, 0.05), 2),
            "ivme_x_g": round(rng.normal(0, 0.05), 3),
            "ivme_y_g": round(rng.normal(0, 0.05), 3),
            "ivme_z_g": round(ozgul_kuvvet / G + rng.normal(0, 0.04), 3),
            "sicaklik_C": round(YER_SICAKLIGI - 0.0065 * h + rng.normal(0, 0.15), 2),
            "durum": durum,
        })

        t = round(t + DT, 3)
        if durum == 7:
            inis_sayac += 1
            if inis_sayac >= 30:  # inişten sonra 3 s daha kayıt
                break

    return pd.DataFrame(kayitlar)


def hata_ekle(df):
    """Temiz veriye test amaçlı bilinen hatalar ekler.

    Dönüş: (hatalı DataFrame, beklenen hataların listesi)
    Hata kayıtlarındaki `zaman_ms` alanı, hatalı satırın zaman damgasıdır.
    """
    rng = np.random.default_rng(TOHUM + 1)
    df = df.copy()
    beklenen = []
    n = len(df)

    # 1) Eksik değerler: 12 hücre boşaltılır
    sensor_sutunlari = ["irtifa_m", "basinc_hPa", "ivme_z_g", "sicaklik_C"]
    eksik_satirlar = rng.choice(np.arange(50, n - 50), size=12, replace=False)
    for i in sorted(eksik_satirlar):
        sutun = sensor_sutunlari[int(rng.integers(0, len(sensor_sutunlari)))]
        df.loc[i, sutun] = np.nan
        beklenen.append({"tip": "EKSIK_DEGER", "zaman_ms": int(df.loc[i, "zaman_ms"]), "sutun": sutun})

    # 2) Sensör sıçramaları: 5 adet fiziksel olarak imkânsız ani değer
    ucus_satirlari = df.index[df["durum"].isin([3, 5, 6])]
    sicrama_satirlari = rng.choice(ucus_satirlari[10:-10], size=5, replace=False)
    sicrama_tanimlari = [
        ("irtifa_m", 4800.0),
        ("irtifa_m", -1200.0),
        ("ivme_z_g", 58.0),
        ("ivme_z_g", -41.0),
        ("irtifa_m", 9999.0),
    ]
    for i, (sutun, deger) in zip(sorted(sicrama_satirlari), sicrama_tanimlari):
        if pd.isna(df.loc[i, sutun]):
            continue
        df.loc[i, sutun] = deger
        beklenen.append({"tip": "SENSOR_SICRAMASI", "zaman_ms": int(df.loc[i, "zaman_ms"]), "sutun": sutun})

    # 3) Geçersiz FSM durum kodu: 1 satır
    gecersiz_satir = int(rng.choice(df.index[df["durum"] == 5]))
    df.loc[gecersiz_satir, "durum"] = 9
    beklenen.append({"tip": "GECERSIZ_DURUM", "zaman_ms": int(df.loc[gecersiz_satir, "zaman_ms"]), "sutun": "durum"})

    # 4) Tekrar eden satırlar: SD karta yazma hatasını taklit eden 8 kopya
    kopya_satirlari = sorted(rng.choice(np.arange(20, n - 20), size=8, replace=False))
    parcalar, onceki = [], 0
    for i in kopya_satirlari:
        parcalar.append(df.iloc[onceki:i + 1])
        parcalar.append(df.iloc[[i]])  # aynı satır bir kez daha yazılır
        beklenen.append({"tip": "DUPLIKE_SATIR", "zaman_ms": int(df.loc[i, "zaman_ms"]), "sutun": "-"})
        onceki = i + 1
    parcalar.append(df.iloc[onceki:])
    df = pd.concat(parcalar, ignore_index=True)

    df["durum"] = df["durum"].astype(int)
    return df, beklenen


def main():
    klasor = Path(__file__).parent / "veri"
    klasor.mkdir(exist_ok=True)

    temiz = ucus_simule_et()
    hatali, beklenen = hata_ekle(temiz)

    hatali.to_csv(klasor / "ucus_log_simule.csv", index=False)
    with open(klasor / "beklenen_hatalar.json", "w", encoding="utf-8") as f:
        json.dump(beklenen, f, ensure_ascii=False, indent=2)

    tepe = temiz.loc[temiz["irtifa_m"].idxmax()]
    print(f"Simüle uçuş üretildi: {len(hatali)} satır ({len(temiz)} temiz + {len(hatali) - len(temiz)} duplike)")
    print(f"Tepe irtifa ≈ {tepe['irtifa_m']:.0f} m, eklenen hata sayısı: {len(beklenen)}")
    print(f"Dosyalar: {klasor / 'ucus_log_simule.csv'}, {klasor / 'beklenen_hatalar.json'}")


if __name__ == "__main__":
    main()
