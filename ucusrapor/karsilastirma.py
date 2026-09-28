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
    if np.isnan(kalkis):
        raise ValueError(f"{yol}: durum sütununda kalkış (durum >= 1) yok")
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


def _hata(ucus, ad):
    """Bir yöntemin gerçek tepe noktasına göre hatası (s). Tespit yoksa None."""
    satir = ucus["tablo"].set_index("yontem")["tespit_s"].get(ad)
    if satir is None or ucus["gercek_tepe_s"] is None or np.isnan(satir):
        return None
    return float(satir - ucus["gercek_tepe_s"])


def cikarimlar(masa, vakumlar, ucus, tolerans_s=1.0):
    """Rapordaki çıkarım cümlelerini sabit yazmak yerine sonuçlardan üretir.

    Kendi test kayıtlarınla çalıştırdığında cümleler de ona göre değişir.
    """
    notlar = {}

    # masa testi
    notlar["masa"] = (f"Özgün kart {masa['sicaklik_artisi_c']:.1f} °C ısınırken irtifa okuması "
                      f"{masa['ozgun_kayma_m']:+.1f} m kaydı (ticari: {masa['ticari_kayma_m']:+.1f} m). "
                      "Ticari kart sıcaklık kaydetmiyor.")

    # vakum testleri
    basit_fark = [v["ozgun_basit_s"] - v["vana_acilis_s"] for v in vakumlar if v["ozgun_basit_s"] is not None]
    ticari_fark = [v["ticari_s"] - v["vana_acilis_s"] for v in vakumlar if v["ticari_s"] is not None]
    ort_basit = float(np.mean(basit_fark)) if basit_fark else None
    if ort_basit is not None and ort_basit < -tolerans_s:
        notlar["vakum"] = (f"Negatif = erken tetikleme. Mevcut algoritma ortalama {abs(ort_basit):.1f} s erken tetikledi; "
                           "vana açılmadan önceki basınç dalgalanması sebep olabilir.")
    else:
        notlar["vakum"] = "Negatif = erken tetikleme."

    # uçuş
    tablo = ucus["tablo"].set_index("yontem")
    u = []
    hata_basit = _hata(ucus, "Basit barometrik (mevcut)")
    if hata_basit is not None and abs(hata_basit) > tolerans_s:
        irtifa = tablo.loc["Basit barometrik (mevcut)", "tespit_irtifa_m"]
        u.append(f"Mevcut algoritma tepe noktasından {abs(hata_basit):.1f} s "
                 f"{'önce' if hata_basit < 0 else 'sonra'}, ~{irtifa:.0f} m'de tetikledi.")
    hata_mach = _hata(ucus, "Mach kilitli + filtreli barometrik")
    if hata_mach is not None and hata_mach < -tolerans_s:
        u.append("Mach kilidi erken açıldı: ivmeden hesaplanan hız düşük çıkıyor (ivmeölçer doyumu olabilir).")
    u.append("Zamanlayıcı süresi simülasyondan alındı; tek başına değil yedek olarak düşünülmeli.")
    notlar["ucus"] = u

    # karar için çıkarımlar
    k = []
    if ucus["gercek_tepe_s"] is None:
        k.append("Gerçek tepe noktası zamanı bilinmediği için uçuştaki yöntemler doğrulanamadı; "
                 "tablodaki tespit anlarını birbirleriyle ve ivme verisiyle karşılaştırın.")
    elif hata_basit is None or abs(hata_basit) > tolerans_s:
        k.append("Özgün kartın mevcut tepe noktası algoritması bu hâliyle kurtarmayı tetiklemek için güvenilir değil.")
    else:
        k.append(f"Özgün kartın mevcut algoritması uçuşta tolerans içinde ({hata_basit:+.2f} s).")
    adaylar = {ad: _hata(ucus, ad) for ad in tablo.index if not ad.startswith("Zamanlayıcı")}
    adaylar = {ad: h for ad, h in adaylar.items() if h is not None}
    if adaylar:
        en_iyi = min(adaylar, key=lambda a: abs(adaylar[a]))
        k.append(f"Uçuş verisinde en yakın sonuç: {en_iyi} ({adaylar[en_iyi]:+.2f} s). "
                 "Aynı testler tekrarlanıp kaydedilerek doğrulanmalı.")
    if ticari_fark:
        k.append(f"Ticari kart {len(ticari_fark)} vakum denemesinde ortalama {np.mean(ticari_fark):+.2f} s "
                 f"(en fazla {max(ticari_fark, key=abs):+.2f} s) farkla tespit etti; ana/yedek kararı iki kart "
                 "karşılaştırılarak verilmeli.")
    notlar["karar"] = k
    return notlar
