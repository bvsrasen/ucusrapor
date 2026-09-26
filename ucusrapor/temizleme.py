"""Özgün UKB kaydındaki bozuk / eksik verileri bulur ve düzeltir."""
import numpy as np

from .okuma import irtifa_hesapla

NOMINAL_DT_MS = 40  # özgün kart 25 Hz kaydediyor


def temizle(df, bozuk_satirlar=(), p0=None):
    """Temizlenmiş tabloyu, yapılan işlemlerin listesini ve zemin basıncını döndürür.

    p0 verilmezse ilk 2 saniyenin medyan basıncı zemin basıncı kabul edilir
    (kart rampada açıldığında da aynısını yapıyor).
    """
    kayit = [{"tip": "BOZUK_SATIR", "t_ms": None, "detay": f"CSV satır {n}", "islem": "okunamadı, atlandı"}
             for n in bozuk_satirlar]
    df = df.copy()

    # aynı satırın iki kez yazılması
    kopya = df.duplicated(keep="first")
    for t in df.loc[kopya, "t_ms"]:
        kayit.append({"tip": "KOPYA_SATIR", "t_ms": int(t), "detay": "", "islem": "silindi"})
    df = df[~kopya].sort_values("t_ms").reset_index(drop=True)

    # I2C okuma hatası: basınç 0 geliyor ya da bir önceki değerde takılı kalıyor
    sifir = df["basinc_pa"] <= 0
    takili = (df["basinc_pa"].diff() == 0) & ~sifir
    for i in df.index[sifir]:
        kayit.append({"tip": "SENSOR_OKUMA_HATASI", "t_ms": int(df.at[i, "t_ms"]), "detay": "basınç = 0",
                      "islem": "interpolasyonla dolduruldu"})
    for i in df.index[takili]:
        kayit.append({"tip": "SENSOR_TAKILMA", "t_ms": int(df.at[i, "t_ms"]),
                      "detay": "basınç önceki örnekle aynı", "islem": "interpolasyonla dolduruldu"})
    df.loc[sifir | takili, "basinc_pa"] = np.nan

    # kayıt boşlukları (SD yazma gecikmesi)
    fark = df["t_ms"].diff()
    for i in df.index[fark > 2.5 * NOMINAL_DT_MS]:
        kayip = int(round(fark[i] / NOMINAL_DT_MS)) - 1
        kayit.append({"tip": "KAYIT_BOSLUGU", "t_ms": int(df.at[i - 1, "t_ms"]),
                      "detay": f"{int(fark[i])} ms, ~{kayip} örnek kayıp", "islem": "doldurulmadı, işaretlendi"})

    df = df.set_index("t_ms")
    df["basinc_pa"] = df["basinc_pa"].interpolate(method="index", limit_direction="both")
    df = df.reset_index()

    if p0 is None:
        p0 = float(df.loc[df["t_ms"] < 2000, "basinc_pa"].median())
    df["irtifa_m"] = irtifa_hesapla(df["basinc_pa"], p0)
    df["t_s"] = df["t_ms"] / 1000.0
    return df, kayit, p0


def veri_kaybi_orani(df, kayit):
    """Kayıt boşluklarında kaybolan örneklerin oranı (%)."""
    kayip = sum(int(k["detay"].split("~")[1].split()[0]) for k in kayit if k["tip"] == "KAYIT_BOSLUGU")
    return 100.0 * kayip / (len(df) + kayip)
