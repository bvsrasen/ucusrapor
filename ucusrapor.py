"""
Özgün ve ticari UKB test kayıtlarını karşılaştırıp Excel raporu üretir.

    python ucusrapor.py                  # veri/ klasöründeki örnek verilerle
    python ucusrapor.py --veri testler/  # kendi kayıtlarınla (aynı dosya adlarıyla)
"""
import argparse
import time
from pathlib import Path

import pandas as pd

from ucusrapor import __version__
from ucusrapor.karsilastirma import masa_testi, ucus_analizi, vakum_testi
from ucusrapor.rapor import rapor_yaz


def main():
    ap = argparse.ArgumentParser(description="UKB test karşılaştırma raporu")
    ap.add_argument("--veri", default="veri", help="test kayıtlarının bulunduğu klasör")
    ap.add_argument("--cikti", default="rapor/UKB_karsilastirma.xlsx")
    ap.add_argument("--zamanlayici", type=float, default=20.9,
                    help="simülasyondan beklenen tepe noktası süresi (s), zamanlayıcı yedeği için")
    args = ap.parse_args()

    bas = time.perf_counter()
    k = Path(args.veri)
    print(f"UçuşRapor {__version__}  –  veri: {k}/")

    masa = masa_testi(k / "masa_ozgun.csv", k / "masa_ticari.csv")
    print(f"  masa testi: özgün kayma {masa['ozgun_kayma_m']:.1f} m, ticari {masa['ticari_kayma_m']:.1f} m")

    vakumlar = []
    for _, r in pd.read_csv(k / "vakum_referans.csv").iterrows():
        n = int(r["deneme"])
        v = vakum_testi(k / f"vakum_{n}_ozgun.csv", k / f"vakum_{n}_ticari.csv", float(r["vana_acilis_s"]), n)
        vakumlar.append(v)
        print(f"  vakum {n}: referans {v['vana_acilis_s']:.1f} s | özgün (mevcut) {v['ozgun_basit_s']:.1f} s"
              f" | özgün (filtreli) {v['ozgun_filtreli_s']:.1f} s | ticari {v['ticari_s']:.1f} s")

    ref = pd.read_csv(k / "ucus_referans.csv").iloc[0]
    ucus = ucus_analizi(k / "ucus_ozgun.csv", float(ref["zemin_basinci_pa"]), args.zamanlayici,
                        float(ref["gercek_tepe_s"]))
    print(f"  uçuş simülasyonu: gerçek tepe {ucus['gercek_tepe_s']:.2f} s")
    for s in ucus["tablo"].itertuples(index=False):
        print(f"      {s.yontem:<38} {s.tespit_s:>6.2f} s")

    ates = pd.read_csv(k / "ateslemeler.csv", dtype=str).fillna("")
    Path(args.cikti).parent.mkdir(parents=True, exist_ok=True)
    rapor_yaz(args.cikti, masa, vakumlar, ucus, ates, k)
    print(f"rapor: {args.cikti}  ({time.perf_counter() - bas:.1f} s)")


if __name__ == "__main__":
    main()
