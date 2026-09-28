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
from ucusrapor.karsilastirma import cikarimlar, masa_testi, ucus_analizi, vakum_testi
from ucusrapor.rapor import rapor_yaz


def _s(x):
    return "-" if x is None or pd.isna(x) else f"{x:.2f} s"


def main():
    ap = argparse.ArgumentParser(description="UKB test karşılaştırma raporu")
    ap.add_argument("--veri", default="veri", help="test kayıtlarının bulunduğu klasör")
    ap.add_argument("--cikti", default="rapor/UKB_karsilastirma.xlsx")
    ap.add_argument("--gercek", action="store_true",
                    help="veriler gerçek test kaydıysa rapordaki 'örnek veri' uyarısını kaldırır")
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
        print(f"  vakum {n}: referans {v['vana_acilis_s']:.1f} s | özgün (mevcut) {_s(v['ozgun_basit_s'])}"
              f" | özgün (filtreli) {_s(v['ozgun_filtreli_s'])} | ticari {_s(v['ticari_s'])}")

    # gerçek bir uçuşta tepe noktasının doğru zamanı bilinmez; o zaman gercek_tepe_s sütunu boş bırakılabilir
    ref = pd.read_csv(k / "ucus_referans.csv").iloc[0]
    gercek = ref.get("gercek_tepe_s")
    gercek = None if gercek is None or pd.isna(gercek) else float(gercek)
    ucus = ucus_analizi(k / "ucus_ozgun.csv", float(ref["zemin_basinci_pa"]), args.zamanlayici, gercek)
    print(f"  uçuş: gerçek tepe {_s(gercek)}")
    for s in ucus["tablo"].itertuples(index=False):
        print(f"      {s.yontem:<38} {_s(s.tespit_s):>8}")

    ates = pd.read_csv(k / "ateslemeler.csv", dtype=str).fillna("")
    Path(args.cikti).parent.mkdir(parents=True, exist_ok=True)
    notlar = cikarimlar(masa, vakumlar, ucus)
    for n in notlar["karar"]:
        print(f"  - {n}")
    rapor_yaz(args.cikti, masa, vakumlar, ucus, ates, k, notlar, ornek_veri=not args.gercek)
    print(f"rapor: {args.cikti}  ({time.perf_counter() - bas:.1f} s)")


if __name__ == "__main__":
    main()
