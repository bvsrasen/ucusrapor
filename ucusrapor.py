"""Paraşüt açma algoritmalarını gerçek uçuş kayıtlarında dener ve raporlar.

    python ucusrapor.py                     # veri/ucuslar altındaki 12 uçuş
    python ucusrapor.py --kayit ucus.csv    # kendi uçuş bilgisayarınızın kaydı

İlk kullanım rapor/ucusrapor.xlsx, docs/sonuclar.md ve docs/ altındaki
grafikleri üretir. İkinci kullanım tek bir kaydı inceler; kaydın en az
t_s, basinc_pa ve ivme_g sütunları olmalı.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from ucusrapor import algoritmalar as alg
from ucusrapor.degerlendirme import ERKEN_S, GEC_S, durum, ozet, ucusu_degerlendir
from ucusrapor.okuma import HZ, oku_kayit, yeniden_ornekle
from ucusrapor.rapor import excel_yaz, gecikme_grafigi, ucus_grafigi

ORNEK_UCUS = "jackpot_launch_2"


def md_tablo(df):
    def bicim(x):
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "-"
        return f"{x:.2f}" if isinstance(x, float) else str(x)
    satirlar = ["| " + " | ".join(map(str, df.columns)) + " |", "|" + "---|" * len(df.columns)]
    satirlar += ["| " + " | ".join(bicim(x) for x in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join(satirlar)


def hassasiyet(ucuslar, tepeler):
    """Önerilen algoritmanın iki parametresi değişince kaç uçuşta zamanında kaldığı."""
    satirlar = []
    for kilit_s in (0.5, 1.0, 2.0):
        for pencere in (15, 25, 50):
            gecikmeler = []
            for ad, d in ucuslar:
                an = alg.tepe_bul(d.t_s, d.basinc_pa, d.ivme_g, filtre="medyan", kilit=True,
                                  pencere=pencere, kilit_s=kilit_s)
                gecikmeler.append(None if an is None else an - tepeler[ad])
            satirlar.append({"kilit_s": kilit_s, "medyan_penceresi_s": pencere / HZ,
                             "zamanında": sum(durum(g) == "zamanında" for g in gecikmeler),
                             "en_geç_s": max(g for g in gecikmeler if g is not None)})
    return pd.DataFrame(satirlar)


def hepsi():
    bilgi = pd.read_csv("veri/ucuslar.csv")
    ucuslar = [(ad, pd.read_csv(f"veri/ucuslar/{ad}.csv")) for ad in bilgi["ucus"]]

    satirlar, olaylar = [], {}
    for ad, d in ucuslar:
        s, o = ucusu_degerlendir(ad, d)
        satirlar += s
        olaylar[ad] = o
    tablo = pd.DataFrame(satirlar)
    oz = ozet(tablo)
    print(oz.to_string(index=False))

    Path("rapor").mkdir(exist_ok=True)
    excel_yaz("rapor/ucusrapor.xlsx", oz, tablo, bilgi)
    gecikme_grafigi("docs/gecikmeler.png", tablo)
    d = dict(ucuslar)[ORNEK_UCUS]
    kararlar = {isim: alg.ALGORITMALAR[isim](d) for isim in ("Basit barometrik", alg.ONERILEN)}
    ucus_grafigi(f"docs/{ORNEK_UCUS}.png", ORNEK_UCUS, d, olaylar[ORNEK_UCUS], kararlar)

    gecikme = tablo.pivot(index="uçuş", columns="algoritma", values="gecikme_s")
    gecikme = gecikme.reindex(index=bilgi["ucus"], columns=list(dict.fromkeys(tablo["algoritma"])))
    gecikme.index.name = "uçuş"
    referans = pd.DataFrame({
        "uçuş": bilgi["ucus"],
        "kalkıştan_tepeye_s": [olaylar[a]["tepe_s"] - olaylar[a]["kalkis_s"] for a in bilgi["ucus"]],
        "motor_bitişi_s": [olaylar[a]["motor_bitisi_s"] - olaylar[a]["kalkis_s"] for a in bilgi["ucus"]],
        "tepe_m (barometre)": [olaylar[a]["tepe_m"] for a in bilgi["ucus"]],
        "tepe_m (kulübün bildirdiği)": bilgi["bildirilen_tepe_m"],
    })

    metin = f"""# Sonuçlar

`python ucusrapor.py` ile üretildi. Kullanılan 12 uçuş ve kaynakları
[veri/ucuslar.csv](../veri/ucuslar.csv) dosyasında.

Gecikme, paraşüt komutunun verildiği an ile gerçek tepe anı arasındaki fark
(saniye). Negatif değer, komutun tepeden önce, yani roket hâlâ yükselirken
verildiği anlamına geliyor. -{ERKEN_S:g} s ile +{GEC_S:g} s arası "zamanında" sayıldı.

## Özet

{md_tablo(oz)}

## Uçuş uçuş gecikmeler (s)

{md_tablo(gecikme.reset_index())}

## Referans tepe noktası

Gerçek tepe anı, uçuştan sonra bütün kayda bakarak bulundu (irtifa 1
saniyelik ortalanmış medyanla filtrelendi, en yüksek nokta alındı). Bu
yöntemle bulunan tepe irtifası, kulübün her uçuş için bildirdiği tepe
irtifasıyla karşılaştırıldı. Süreler kalkıştan itibaren.

{md_tablo(referans)}

## Önerilen algoritmanın parametrelere hassasiyeti

Önerilen algoritmayı bu 12 uçuşa bakarak seçtim. Seçimin iki parametreye
çok hassas olup olmadığını görmek için motor bitişinden sonraki kilit
süresini ve medyan penceresini değiştirdim.

{md_tablo(hassasiyet(ucuslar, {a: o["tepe_s"] for a, o in olaylar.items()}))}

![Gecikmeler](gecikmeler.png)

![{ORNEK_UCUS}]({ORNEK_UCUS}.png)
"""
    Path("docs/sonuclar.md").write_text(metin, encoding="utf-8")


def tek_kayit(yol):
    d = yeniden_ornekle(oku_kayit(yol))
    ad = Path(yol).stem
    s, o = ucusu_degerlendir(ad, d)
    print(f"{ad}: kalkıştan {o['tepe_s'] - o['kalkis_s']:.2f} s sonra tepe, {o['tepe_m']:.0f} m")
    print(pd.DataFrame(s)[["algoritma", "açılma_s", "gecikme_s", "durum"]].round(2).to_string(index=False))
    Path("rapor").mkdir(exist_ok=True)
    kararlar = {isim: alg.ALGORITMALAR[isim](d) for isim in ("Basit barometrik", alg.ONERILEN)}
    ucus_grafigi(f"rapor/{ad}.png", ad, d, o, kararlar)
    print(f"grafik: rapor/{ad}.png")


def main():
    ap = argparse.ArgumentParser(description="Paraşüt açma algoritmalarını gerçek uçuş kayıtlarında dener.")
    ap.add_argument("--kayit", help="tek bir uçuş kaydı (t_s, basinc_pa, ivme_g sütunlu CSV)")
    args = ap.parse_args()
    if args.kayit:
        tek_kayit(args.kayit)
    else:
        hepsi()


if __name__ == "__main__":
    main()
