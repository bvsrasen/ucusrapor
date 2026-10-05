"""NCSU roket kulübünün gerçek uçuş kayıtlarını indirip analiz tablolarına çevirir.

    python veri_hazirla.py   # veri/ucuslar/*.csv ve veri/ucuslar.csv

Kayıtlar NC State University High-Powered Rocketry Club'ın AirbrakesV2
reposundan (MIT lisansı) belirli commit'lere sabitlenerek indiriliyor; böylece
aynı dosyalar her zaman yeniden elde edilebiliyor. Ham dosyalar (~200 MB)
veri/ham/ altına iniyor ve repoya girmiyor. Repoya giren tablolar 50 Hz'e
getirilmiş, kalkıştan 5 s önce başlayıp en fazla 120 s süren kesitler.
"""
import urllib.request
from pathlib import Path

import pandas as pd

from ucusrapor.okuma import HZ, oku_firm, oku_ncsu_imu, yeniden_ornekle
from ucusrapor.olaylar import kalkis_indeksi

KAYNAK = "https://raw.githubusercontent.com/NCSU-High-Powered-Rocketry-Club/AirbrakesV2"
# Eski sensörün (Parker-LORD 3DM-CX5) kayıtları bu commit'ten sonra repodan silindi
ESKI = "c242c660b9105aea39350e5a1b6d5424f52704a4"
FIRM = "8c51e14c76cf9e3601b7bf2ea79967c6b8a055d1"

# ad, commit, yol, biçim, NCSU'nun kendi notlarından kısa açıklama
UCUSLAR = [
    ("genesis_launch_1", ESKI, "launch_data/old_imu_launches/genesis_launch_1.csv", "imu",
     "Hava freni denemesi; frenler süzülmede açılmadı."),
    ("genesis_launch_2", ESKI, "launch_data/old_imu_launches/genesis_launch_2.csv", "imu",
     "Aynı günün ikinci uçuşu; frenler yine zamanında açılmadı."),
    ("legacy_launch_1", ESKI, "launch_data/old_imu_launches/legacy_launch_1.csv", "imu",
     "Kayıtta zaman atlaması ve birkaç saniyelik eksik veri var."),
    ("pelicanator_launch_1", ESKI, "launch_data/old_imu_launches/pelicanator_launch_1.csv", "imu",
     "Frenlerin tam çalıştığı ilk uçuş; kayıt inişten önce kesiliyor."),
    ("pelicanator_launch_2", ESKI, "launch_data/old_imu_launches/pelicanator_launch_2.csv", "imu",
     "Rüzgârlı bir gün; frenler açılmadı."),
    ("pelicanator_launch_4", ESKI, "launch_data/old_imu_launches/pelicanator_launch_4.csv", "imu",
     "NASA Student Launch 2025 yarışma uçuşu."),
    ("government_work_1", ESKI, "launch_data/old_imu_launches/government_work_1_time_fix.csv", "imu",
     "Küçük ölçekli roket; frenler süzülmenin başında açıldı."),
    ("government_work_2", ESKI, "launch_data/old_imu_launches/government_work_2.csv", "imu",
     "Yeni tepe tahmini yazılımının denendiği sorunsuz uçuş."),
    ("jackpot_launch_1", FIRM, "launch_data/real_firm_launches/jackpot_launch_1.csv", "firm",
     "FIRM kartının tek sensör olarak kullanıldığı ilk uçuş; frenler süzülmenin hemen başında açıldı."),
    ("jackpot_launch_2", FIRM, "launch_data/real_firm_launches/jackpot_launch_2.csv", "firm",
     "Frenler içeriden sızdırmaz değildi; açılınca büyük bir basınç sıçraması oldu."),
    ("jackpot_launch_3", FIRM, "launch_data/real_firm_launches/jackpot_launch_3.csv", "firm",
     "Frenler çalıştı; ana paraşüt ipleri dolandı."),
    ("jackpot_launch_4", FIRM, "launch_data/real_firm_launches/jackpot_launch_4.csv", "firm",
     "NASA Student Launch 2026 yarışma uçuşu; frenler tepeye yakın kısa süre açıldı."),
]
METADATA = [(ESKI, "launch_data/metadata.json"), (FIRM, "launch_data/metadata.json")]
# Kulübün metadata'sında yıl 2025 yazıyor ama kayıttaki zaman damgaları 7 Şubat 2026'yı gösteriyor
TARIH_DUZELTME = {"government_work_2": "2026-02-07"}


def indir(commit, yol, hedef):
    if not hedef.exists():
        hedef.parent.mkdir(parents=True, exist_ok=True)
        print(f"  indiriliyor: {yol}")
        urllib.request.urlretrieve(f"{KAYNAK}/{commit}/{yol}", hedef)
    return hedef


def main():
    ham, cikti = Path("veri/ham"), Path("veri/ucuslar")
    cikti.mkdir(parents=True, exist_ok=True)

    bilgi = {}
    for commit, yol in METADATA:
        m = pd.read_json(indir(commit, yol, ham / commit[:7] / "metadata.json"), typ="series")
        bilgi.update(m.to_dict())

    satirlar = []
    for ad, commit, yol, bicim, not_ in UCUSLAR:
        dosya = indir(commit, yol, ham / commit[:7] / Path(yol).name)
        d = oku_ncsu_imu(dosya) if bicim == "imu" else oku_firm(dosya)
        d = yeniden_ornekle(d)
        k = kalkis_indeksi(d["ivme_g"])
        d = d.iloc[max(0, k - int(5 * HZ)):k + int(120 * HZ)].reset_index(drop=True)
        d["t_s"] = (d["t_s"] - d["t_s"].iloc[0]).round(2)
        d["basinc_pa"] = d["basinc_pa"].round(2)
        d["ivme_g"] = d["ivme_g"].round(4)
        d.to_csv(cikti / f"{ad}.csv", index=False)

        m = bilgi.get(Path(yol).name.replace("_time_fix", ""), {})
        satirlar.append({
            "ucus": ad,
            "tarih": TARIH_DUZELTME.get(ad, m.get("date", "")[:10]),
            "yer": m.get("launch_site", {}).get("location", ""),
            "sensor": m.get("ins_details", {}).get("ins_model", ""),
            "bildirilen_tepe_m": m.get("flight_data", {}).get("apogee_meters"),
            "not": not_,
            "kaynak": f"AirbrakesV2@{commit[:7]}/{yol}",
        })
        print(f"{ad}: {len(d)} örnek")
    pd.DataFrame(satirlar).to_csv("veri/ucuslar.csv", index=False)


if __name__ == "__main__":
    main()
