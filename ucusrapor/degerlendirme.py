"""Algoritmaları uçuşlarda çalıştırıp referans tepe noktasıyla karşılaştırır."""
import numpy as np
import pandas as pd

from ucusrapor.algoritmalar import ALGORITMALAR, ncsu_karari
from ucusrapor.olaylar import olaylar

# Tepe noktasında dikey hız sıfır; 1 s önce roket hâlâ ~10 m/s ile çıkıyor,
# 2 s sonra ~20 m/s ile düşüyor. Bu aralığın dışı paraşüt için risk.
ERKEN_S = 1.0
GEC_S = 2.0


def durum(gecikme):
    if gecikme is None:
        return "açılmadı"
    if gecikme < -ERKEN_S:
        return "erken"
    if gecikme > GEC_S:
        return "geç"
    return "zamanında"


def ucusu_degerlendir(ad, d):
    """Bir uçuş için her algoritmanın satırı."""
    o = olaylar(d)
    kararlar = {isim: f(d) for isim, f in ALGORITMALAR.items()}
    if "ncsu_durum" in d.columns:
        kararlar["NCSU uçuş yazılımı"] = ncsu_karari(d["t_s"], d["ncsu_durum"])
    satirlar = []
    for isim, an in kararlar.items():
        gecikme = None if an is None else an - o["tepe_s"]
        satirlar.append({"uçuş": ad, "algoritma": isim, "tepe_s": o["tepe_s"] - o["kalkis_s"],
                         "açılma_s": None if an is None else an - o["kalkis_s"],
                         "gecikme_s": gecikme, "durum": durum(gecikme)})
    return satirlar, o


def ozet(tablo):
    """Algoritma başına: kaç uçuşta zamanında/erken/geç, gecikme aralığı."""
    satirlar = []
    for isim, g in tablo.groupby("algoritma", sort=False):
        zamaninda = g[g["durum"] == "zamanında"]["gecikme_s"]
        satirlar.append({
            "algoritma": isim,
            "uçuş": len(g),
            "zamanında": int((g["durum"] == "zamanında").sum()),
            "erken": int((g["durum"] == "erken").sum()),
            "geç": int((g["durum"] == "geç").sum()),
            "açılmadı": int((g["durum"] == "açılmadı").sum()),
            "en_erken_s": float(g["gecikme_s"].min()),
            "en_geç_s": float(g["gecikme_s"].max()),
            "zamanında_ortalama_s": float(zamaninda.mean()) if len(zamaninda) else np.nan,
        })
    return pd.DataFrame(satirlar)
