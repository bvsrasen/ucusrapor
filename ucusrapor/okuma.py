"""Özgün ve ticari UKB kayıtlarını okuyup ortak bir tabloya çeviren fonksiyonlar."""
from pathlib import Path

import numpy as np
import pandas as pd

OZGUN_SUTUNLAR = ["t_ms", "basinc_pa", "sicaklik_c", "ax_g", "ay_g", "az_g", "durum"]


def oku_ozgun(yol):
    """Özgün kartın SD kayıtlarını okur.

    Güç kesildiğinde son satır yarım kalabiliyor ya da SD kart bozuk satır
    yazabiliyor. Bunları atlayıp satır numaralarını ayrıca döndürüyoruz.
    """
    satirlar, bozuk = [], []
    with open(yol, encoding="utf-8", errors="replace") as f:
        baslik = f.readline().strip().split(",")
        if baslik != OZGUN_SUTUNLAR:
            raise ValueError(f"{Path(yol).name}: beklenmeyen başlık {baslik}")
        for no, satir in enumerate(f, start=2):
            parca = satir.strip().split(",")
            try:
                if len(parca) != len(OZGUN_SUTUNLAR):
                    raise ValueError
                satirlar.append([float(x) for x in parca])
            except ValueError:
                bozuk.append(no)
    df = pd.DataFrame(satirlar, columns=OZGUN_SUTUNLAR)
    df["t_ms"] = df["t_ms"].astype(int)
    df["durum"] = df["durum"].astype(int)
    return df, bozuk


def oku_ticari(yol):
    """Ticari kartın dışa aktardığı CSV (zaman_s, irtifa_m, olay)."""
    df = pd.read_csv(yol, dtype={"olay": str}).fillna({"olay": ""})
    if not {"zaman_s", "irtifa_m"}.issubset(df.columns):
        raise ValueError(f"{Path(yol).name}: zaman_s / irtifa_m sütunları yok")
    return df


def irtifa_hesapla(basinc_pa, p0):
    """Standart atmosfer modeliyle basınçtan irtifa (zemine göre, m)."""
    return (1 - (np.asarray(basinc_pa, dtype=float) / p0) ** 0.190263) / 2.25577e-5
