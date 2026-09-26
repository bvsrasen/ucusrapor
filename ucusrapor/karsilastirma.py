"""Testlerdeki özgün ve ticari UKB kayıtlarını karşılaştırır."""
import numpy as np
import pandas as pd

from .apogee import basit_barometrik, filtreli_barometrik, hepsini_dene
from .okuma import oku_ozgun, oku_ticari
from .temizleme import temizle, veri_kaybi_orani


def ticari_kayip_orani(tc, nominal_s=0.05):
    """Ticari kaydın zaman damgalarındaki boşluklardan kayıp örnek oranı (%)."""
    fark = tc["zaman_s"].diff().dropna()
    kayip = ((fark[fark > 2.5 * nominal_s] / nominal_s).round() - 1).sum()
    return float(100.0 * kayip / (len(tc) + kayip))


def masa_testi(ozgun_yolu, ticari_yolu):
    d, bozuk = oku_ozgun(ozgun_yolu)
    df, kayit, _ = temizle(d, bozuk)
    tc = oku_ticari(ticari_yolu)
    son = df["t_s"].max()
    return {
        "ozgun": df, "ticari": tc, "kayit": kayit,
        "ozgun_gurultu_m": float((df["irtifa_m"] - df["irtifa_m"].rolling(50, center=True).mean()).std()),
        "ticari_gurultu_m": float((tc["irtifa_m"] - tc["irtifa_m"].rolling(40, center=True).mean()).std()),
        "ozgun_kayma_m": float(df.loc[df["t_s"] > son - 30, "irtifa_m"].mean() - df.loc[df["t_s"] < 30, "irtifa_m"].mean()),
        "ticari_kayma_m": float(tc.loc[tc["zaman_s"] > son - 30, "irtifa_m"].mean() - tc.loc[tc["zaman_s"] < 30, "irtifa_m"].mean()),
        "ozgun_kayip_yuzde": veri_kaybi_orani(df, kayit),
        "ticari_kayip_yuzde": ticari_kayip_orani(tc),
        "sicaklik_artisi_c": float(df.loc[df["t_s"] > son - 30, "sicaklik_c"].mean() - df.loc[df["t_s"] < 30, "sicaklik_c"].mean()),
    }


def saat_farkini_bul(ozgun, ticari, aralik=(0.0, 3.0), adim=0.05):
    """İki kartın saatleri senkron değil. Ticari kaydı kaydırıp irtifa eğrilerinin
    en iyi örtüştüğü kaydırmayı buluyoruz."""
    t_o, h_o = ozgun["t_s"].to_numpy(), ozgun["irtifa_m"].to_numpy()
    en_iyi, en_az = 0.0, np.inf
    for fark in np.arange(aralik[0], aralik[1] + 1e-9, adim):
        h_t = np.interp(t_o, ticari["zaman_s"].to_numpy() + fark, ticari["irtifa_m"].to_numpy(),
                        left=np.nan, right=np.nan)
        hata = np.nanmean((h_o - h_t) ** 2)
        if hata < en_az:
            en_iyi, en_az = fark, hata
    return round(float(en_iyi), 2)


def vakum_testi(ozgun_yolu, ticari_yolu, vana_acilis_s, deneme):
    d, bozuk = oku_ozgun(ozgun_yolu)
    df, kayit, _ = temizle(d, bozuk)
    tc = oku_ticari(ticari_yolu)
    fark = saat_farkini_bul(df, tc)
    tc = tc.assign(zaman_hizali_s=tc["zaman_s"] + fark)
    t, h = df["t_s"].to_numpy(), df["irtifa_m"].to_numpy()
    ticari_tepe = tc.loc[tc["olay"] == "APOGEE", "zaman_hizali_s"]
    return {
        "deneme": deneme, "ozgun": df, "ticari": tc, "kayit": kayit, "saat_farki_s": fark,
        "vana_acilis_s": vana_acilis_s,
        "maks_irtifa_esdegeri_m": float(df["irtifa_m"].max()),
        "ozgun_basit_s": basit_barometrik(t, h),
        "ozgun_filtreli_s": filtreli_barometrik(t, h),
        "ticari_s": float(ticari_tepe.iloc[0]) if len(ticari_tepe) else None,
        "ozgun_kayip_yuzde": veri_kaybi_orani(df, kayit),
    }


def ucus_analizi(yol, zemin_basinci, zamanlayici_s, gercek_tepe_s=None):
    d, bozuk = oku_ozgun(yol)
    df, kayit, _ = temizle(d, bozuk, p0=zemin_basinci)
    kalkis = float(df.loc[df["durum"] >= 1, "t_s"].min())
    yontemler = hepsini_dene(df, kalkis, zamanlayici_s)
    tablo = []
    for ad, tespit in yontemler.items():
        satir = {"yontem": ad, "tespit_s": None if tespit is None else round(tespit - kalkis, 2)}
        if tespit is not None:
            i = int(np.argmin(np.abs(df["t_s"].to_numpy() - tespit)))
            satir["tespit_irtifa_m"] = round(float(df["irtifa_m"].iloc[i]), 0)
        tablo.append(satir)
    return {"df": df, "kayit": kayit, "kalkis_s": kalkis, "tablo": pd.DataFrame(tablo),
            "gercek_tepe_s": gercek_tepe_s, "kayip_yuzde": veri_kaybi_orani(df, kayit)}
