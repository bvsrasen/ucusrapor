"""
Tepe noktası yöntemlerini tek bir örnek uçuşla değil, farklı gürültü ve SD kart
bozulmalarıyla üretilmiş çok sayıda uçuşla dener.

Tek bir örnek uçuşta bir yöntemin tutması şans olabilir; burada her yöntemin kaç
uçuşta 1 s içinde tespit ettiğini sayıyoruz.

    python ucus_tekrar.py            # 100 uçuş
    python ucus_tekrar.py --n 300
"""
import argparse
import tempfile
from collections import defaultdict
from pathlib import Path

import numpy as np

import veri_uret
from ucusrapor.karsilastirma import ucus_analizi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100, help="simüle edilecek uçuş sayısı")
    ap.add_argument("--tolerans", type=float, default=1.0, help="uygun sayılan en büyük hata (s)")
    ap.add_argument("--zamanlayici", type=float, default=20.9, help="zamanlayıcı yedeğinin süresi (s)")
    args = ap.parse_args()

    hatalar = defaultdict(list)
    with tempfile.TemporaryDirectory() as gecici:
        veri_uret.KLASOR = Path(gecici)
        for i in range(args.n):
            bilgi = veri_uret.ucus(np.random.default_rng(1000 + i))
            u = ucus_analizi(Path(gecici) / "ucus_ozgun.csv", bilgi["zemin_basinci_pa"], args.zamanlayici,
                             bilgi["gercek_tepe_s"])
            for s in u["tablo"].itertuples(index=False):
                hatalar[s.yontem].append(np.nan if s.tespit_s is None else s.tespit_s - bilgi["gercek_tepe_s"])

    print(f"{args.n} uçuş, tolerans ±{args.tolerans:g} s\n")
    print(f"{'Yöntem':<38} {'uygun':>6} {'erken':>6} {'geç':>6} {'medyan hata':>12}")
    for ad, h in hatalar.items():
        h = np.array(h, dtype=float)
        uygun = np.mean(np.abs(h) <= args.tolerans) * 100
        erken = np.mean(h < -args.tolerans) * 100
        gec = np.mean(h > args.tolerans) * 100
        print(f"{ad:<38} {uygun:5.0f}% {erken:5.0f}% {gec:5.0f}% {np.nanmedian(h):+11.2f} s")


if __name__ == "__main__":
    main()
