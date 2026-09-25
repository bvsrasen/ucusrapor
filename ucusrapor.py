"""
UçuşRapor - Komut satırı arayüzü
===============================

Ham uçuş log dosyasını tek komutla okur, temizler, metrikleri hesaplar ve
standart Excel raporunu üretir (NFR-02: tek komutla çalıştırma).

Kullanım:
    python ucusrapor.py veri/ucus_log_simule.csv
    python ucusrapor.py veri/ucus_log_simule.csv --cikti rapor/Test_1.xlsx
    python ucusrapor.py gercek_log.csv --gercek      (simüle uyarısını kaldırır)
"""

import argparse
import sys
import time
from pathlib import Path

from ucusrapor import __version__
from ucusrapor.isleme import VeriFormatHatasi, metrikleri_hesapla, temizle, veri_oku, zenginlestir
from ucusrapor.rapor import excel_raporu_olustur, rapor_bilgisi


def arguman_al():
    p = argparse.ArgumentParser(description="UçuşRapor: roket uçuş logundan otomatik Excel raporu üretir.")
    p.add_argument("log_dosyasi", help="Ham uçuş log dosyası (CSV)")
    p.add_argument("--cikti", help="Excel rapor dosyasının yolu (varsayılan: rapor/<log_adı>_rapor.xlsx)")
    p.add_argument("--gercek", action="store_true", help="Gerçek uçuş verisi (rapordaki simüle uyarısını kaldırır)")
    p.add_argument("--version", action="version", version=f"UçuşRapor {__version__}")
    return p.parse_args()


def main():
    args = arguman_al()
    baslangic = time.perf_counter()
    log = Path(args.log_dosyasi)

    print(f"\n🚀 UçuşRapor {__version__}")
    print("─" * 52)
    try:
        ham = veri_oku(log)
    except (FileNotFoundError, VeriFormatHatasi) as e:
        print(f"❌ Hata: {e}")
        sys.exit(1)
    print(f"[1/4] Log okundu ..................... {len(ham):>5} satır")

    sonuc = temizle(ham)
    print(f"[2/4] Veri temizlendi ................ {len(sonuc.kayitlar):>5} sorun işlendi")
    for tip, adet in sorted(sonuc.ozet().items()):
        print(f"        • {tip:<22} {adet:>3}")

    df = zenginlestir(sonuc.temiz)
    m = metrikleri_hesapla(df)
    print("[3/4] Metrikler hesaplandı")
    print(f"        • Maksimum irtifa ........ {m['maks_irtifa_m']:>8.1f} m  (t = {m['apogee_zamani_s']:.1f} s)")
    print(f"        • Maksimum ivme .......... {m['maks_ivme_g']:>8.2f} g")
    print(f"        • Sürüklenme paraşütü .... {m['suruklenme_parasutu_s']:>8.1f} s")
    print(f"        • Ana paraşüt ............ {m['ana_parasut_s']:>8.1f} s  ({m['ana_parasut_irtifa_m']:.0f} m)")
    print(f"        • Toplam uçuş süresi ..... {m['ucus_suresi_s']:>8.1f} s")

    cikti = Path(args.cikti) if args.cikti else Path("rapor") / f"{log.stem}_rapor.xlsx"
    cikti.parent.mkdir(parents=True, exist_ok=True)
    sure = time.perf_counter() - baslangic
    excel_raporu_olustur(df, sonuc, m, cikti, rapor_bilgisi(log.name, sure, simule=not args.gercek))
    toplam = time.perf_counter() - baslangic
    print(f"[4/4] Excel raporu oluşturuldu ....... {cikti}")
    print("─" * 52)
    print(f"✅ Tamamlandı: {toplam:.2f} saniye (hedef < 300 s)\n")


if __name__ == "__main__":
    main()
