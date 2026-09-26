"""
Örnek test verisi üretici.

Gerçek test kayıtlarımız olmadığı için (testlerde veriyi sadece ekrandan izledik,
kaydetmedik) aracı geliştirirken bu betikle ürettiğim örnek verileri kullandım.
Değerler TEKNOFEST Orta İrtifa sınıfı bir roketin profiline göre ayarlandı
(asgari 8000 ft, hedef ~3 km, yanma sonunda ~Mach 1.1).

Üretilen dosyalar:
  veri/masa_ozgun.csv, veri/masa_ticari.csv          masa (durağan) testi, 10 dk
  veri/vakum_1..3_ozgun.csv, veri/vakum_1..3_ticari.csv  vakum odası denemeleri
  veri/ucus_ozgun.csv                                 uçuş simülasyonu (özgün UKB log formatında)
  veri/ateslemeler.csv                                yer ateşleme test formu
  veri/vakum_referans.csv                             vakum denemelerinde vananın açıldığı an (el ile not)

Özgün UKB formatı : t_ms, basinc_pa, sicaklik_c, ax_g, ay_g, az_g, durum
Ticari UKB formatı: zaman_s, irtifa_m, olay   (1 m çözünürlük, 20 Hz)
"""
import csv
from pathlib import Path

import numpy as np

KLASOR = Path(__file__).parent / "veri"
P0_LAB = 101250.0      # İstanbul'daki laboratuvar zemin basıncı (Pa)
P0_SAHA = 90650.0      # Aksaray atış alanı zemin basıncı (Pa), ~950 m rakım
G = 9.80665


def basinc(h, p0):
    return p0 * (1 - 2.25577e-5 * h) ** 5.25588


def irtifa(p, p0):
    return (1 - (p / p0) ** 0.190263) / 2.25577e-5


# ---------------------------------------------------------------- özgün UKB kusurları
def ozgun_kaydi_boz(satirlar, rng, bosluk_olasiligi=0.004, i2c_olasiligi=0.003, kopya_olasiligi=0.002):
    """SD kart / sensör kaynaklı gerçekçi bozulmalar ekler.

    - SD yazma gecikmesi: arada 150-600 ms'lik veri kaybı
    - I2C okuma hatası: basınç 0 ya da bir önceki değerin aynısı (takılı kalma)
    - Aynı satırın iki kez yazılması
    - Kaydın sonunda yarım kalmış satır (güç kesilince)
    """
    cikti, atla = [], 0
    for i, s in enumerate(satirlar):
        if atla:
            atla -= 1
            continue
        if rng.random() < bosluk_olasiligi:
            atla = int(rng.integers(4, 15))
            continue
        s = list(s)
        r = rng.random()
        if r < i2c_olasiligi / 2:
            s[1] = 0
        elif r < i2c_olasiligi and cikti:
            s[1] = cikti[-1][1]
        cikti.append(s)
        if rng.random() < kopya_olasiligi:
            cikti.append(list(s))
    return cikti


def yaz_ozgun(yol, satirlar, yarim_satir=True):
    with open(yol, "w", newline="") as f:
        f.write("t_ms,basinc_pa,sicaklik_c,ax_g,ay_g,az_g,durum\n")
        for s in satirlar:
            f.write(f"{s[0]},{s[1]:.0f},{s[2]:.2f},{s[3]:.2f},{s[4]:.2f},{s[5]:.2f},{s[6]}\n")
        if yarim_satir:
            f.write(f"{satirlar[-1][0] + 40},{satirlar[-1][1]:.0f},2")  # güç kesildiğinde yarım kalan satır


def yaz_ticari(yol, satirlar):
    with open(yol, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["zaman_s", "irtifa_m", "olay"])
        w.writerows(satirlar)


# ---------------------------------------------------------------- masa testi
def masa_testi(rng):
    sure, dt_o, dt_t = 600.0, 0.04, 0.05
    t = np.arange(0, sure, dt_o)
    sicaklik = 22.0 + 9.0 * (1 - np.exp(-t / 180))            # kart ısınıyor
    # basınç sensörünün sıcaklıkla kayması + oda basıncının yavaş değişimi
    p = P0_LAB - 4.0 * (sicaklik - 22.0) + 6 * np.sin(t / 120) + rng.normal(0, 3.2, t.size)
    ozgun = [[int(round(ti * 1000)), pi, si + rng.normal(0, 0.05), rng.normal(0, 0.012), rng.normal(0, 0.012),
              1.0 + rng.normal(0, 0.015), 0] for ti, pi, si in zip(t, p, sicaklik)]
    ozgun = ozgun_kaydi_boz(ozgun, rng)
    yaz_ozgun(KLASOR / "masa_ozgun.csv", ozgun)

    tt = np.arange(0, sure, dt_t)
    h = irtifa(P0_LAB + 6 * np.sin(tt / 120) + rng.normal(0, 4, tt.size), P0_LAB)
    yaz_ticari(KLASOR / "masa_ticari.csv", [[f"{a:.2f}", int(round(b)), ""] for a, b in zip(tt, h)])


# ---------------------------------------------------------------- vakum odası
def vakum_denemesi(no, rng):
    """Pompa ile basınç ~3 km irtifa eşdeğerine düşürülür, sonra vana elle açılır."""
    hedef_p = basinc(3000 + rng.normal(0, 150), P0_LAB)
    inis_suresi = 55 + rng.normal(0, 5)
    bekleme = 4 + rng.random() * 3
    vana_t = 5 + inis_suresi + bekleme       # vananın açıldığı an (referans "apogee")
    toplam = vana_t + 45

    def oda_basinci(t):
        if t < 5:
            return P0_LAB
        if t < 5 + inis_suresi:
            x = (t - 5) / inis_suresi
            return P0_LAB - (P0_LAB - hedef_p) * (1 - np.exp(-3.2 * x)) / (1 - np.exp(-3.2))
        if t < vana_t:
            return hedef_p
        return P0_LAB - (P0_LAB - hedef_p) * np.exp(-(t - vana_t) / 11)

    def pompa_titresimi(t):
        # pompa çalışırken oda basıncında birkaç Hz'lik dalgalanma oluyor
        return 140 * np.sin(2 * np.pi * 2.3 * t) + 60 * np.sin(2 * np.pi * 5.1 * t) if 5 <= t < vana_t else 0.0

    t_o = np.arange(0, toplam, 0.04)
    ozgun = []
    for t in t_o:
        p = oda_basinci(t) + pompa_titresimi(t) + rng.normal(0, 3.5)
        ozgun.append([int(round(t * 1000)), p, 23 + rng.normal(0, 0.05), rng.normal(0, 0.01), rng.normal(0, 0.01),
                      1 + rng.normal(0, 0.015), 0])
    ozgun = ozgun_kaydi_boz(ozgun, rng)
    yaz_ozgun(KLASOR / f"vakum_{no}_ozgun.csv", ozgun)

    # ticari kart kendi filtresinden geçirip 1 m çözünürlükle yazıyor; saati özgün karttan ~1,3 s geride başlıyor
    saat_farki = 1.3 + rng.random() * 0.4
    t_t = np.arange(0, toplam - saat_farki, 0.05)
    ticari, tepe_bulundu, en_yuksek, dusus = [], False, -1e9, 0
    h_filtre = 0.0
    for t in t_t:
        gercek_t = t + saat_farki
        h_ham = irtifa(oda_basinci(gercek_t) + 0.15 * pompa_titresimi(gercek_t) + rng.normal(0, 4), P0_LAB)
        h_filtre = 0.8 * h_filtre + 0.2 * h_ham
        olay = ""
        if not tepe_bulundu:
            if h_filtre > en_yuksek:
                en_yuksek, dusus = h_filtre, 0
            elif h_filtre < en_yuksek - 5:
                dusus += 1
                if dusus >= 10:
                    olay, tepe_bulundu = "APOGEE", True
        ticari.append([f"{t:.2f}", int(round(h_filtre)), olay])
    yaz_ticari(KLASOR / f"vakum_{no}_ticari.csv", ticari)
    return {"deneme": no, "vana_acilis_s": round(vana_t, 2), "ticari_saat_farki_s": round(saat_farki, 2)}


# ---------------------------------------------------------------- uçuş simülasyonu
def ucus(rng):
    """Orta irtifa uçuşu. Yanma sonunda ~Mach 1.1; ses hızı civarında statik basınç ölçümü bozuluyor."""
    dt, t, h, v = 0.04, 0.0, 0.0, 0.0
    rampa, yanma = 2.0, 3.4
    m0, m1, cd_a = 24.0, 20.5, 0.021
    satirlar = []

    def itki(tu):
        if tu < 0 or tu > yanma:
            return 0.0
        return 5600 if tu < 0.25 else 3900 - 700 * (tu / yanma)

    tepe_t, tepe_h = None, None
    vmaks = 0.0
    while True:
        tu = t - rampa
        durum = 0 if tu < 0 else (1 if tu < 0.3 else (2 if tu < yanma else 3))
        m = m0 - (m0 - m1) * min(max(tu, 0) / yanma, 1)
        rho = 1.05 * np.exp(-h / 8500)
        surukleme = 0.5 * rho * cd_a * v * abs(v) * (1.45 if 0.95 < abs(v) / 335 < 1.15 else 1.0)
        a = (itki(tu) - surukleme) / m - G if tu >= 0 else 0.0
        v += a * dt
        h = max(h + v * dt, 0.0)
        if tepe_t is None and tu > 5 and v <= 0:
            tepe_t, tepe_h = t, h
        mach = abs(v) / (340 - 0.004 * h)

        p = basinc(h, P0_SAHA)
        # transonik bölgede statik porttaki basınç hatası (önce düşük, sonra yüksek okuma)
        if 0.85 < mach < 1.25:
            x = (mach - 0.85) / 0.4
            p += -3200 * np.sin(np.pi * x) * (1 if v > 0 else 0) + 1800 * np.sin(2 * np.pi * x) * (1 if x > 0.5 else 0)
        p += rng.normal(0, 4 + 30 * (durum in (1, 2)))            # motor titreşimi gürültüyü artırıyor
        az = min((a + G) / G + rng.normal(0, 0.08 + 0.6 * (durum in (1, 2))), 16.0)  # ±16 g'de doyuma giriyor
        satirlar.append([int(round(t * 1000)), p, 24 - 0.0065 * h + rng.normal(0, 0.1),
                         rng.normal(0, 0.2 + 0.5 * (durum in (1, 2))), rng.normal(0, 0.2 + 0.5 * (durum in (1, 2))), az, durum])
        t += dt
        if tepe_t and t > tepe_t + 12:
            break
    # uçuşta titreşim yüzünden SD kaybı daha sık
    satirlar = ozgun_kaydi_boz(satirlar, rng, bosluk_olasiligi=0.007, i2c_olasiligi=0.006, kopya_olasiligi=0.003)
    yaz_ozgun(KLASOR / "ucus_ozgun.csv", satirlar)
    return {"gercek_tepe_s": round(tepe_t - rampa, 2), "gercek_tepe_m": round(tepe_h, 1),
            "rampa_s": rampa, "zemin_basinci_pa": P0_SAHA}


def ateslemeler():
    # yer ateşleme testlerinde tuttuğumuz formun örnek hâli
    satirlar = [
        ["1", "özgün", "0.8", "1.2", "32", "hayır", "barut yetmedi, burun konisi oynadı ama çıkmadı"],
        ["2", "özgün", "1.2", "1.3", "29", "evet", ""],
        ["3", "ticari", "1.2", "1.1", "", "evet", "komut-ateşleme gecikmesi ölçülemedi (ticari kart iç zamanlama)"],
        ["4", "özgün", "1.2", "0.0", "", "hayır", "süreklilik yok, konnektör gevşek; yeniden takıldı"],
        ["5", "özgün", "1.2", "1.2", "31", "evet", ""],
        ["6", "ticari", "1.2", "1.2", "", "evet", ""],
    ]
    with open(KLASOR / "ateslemeler.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["deneme", "ukb", "barut_g", "sureklilik_ohm", "gecikme_ms", "ayrilma", "not"])
        w.writerows(satirlar)


def main():
    KLASOR.mkdir(exist_ok=True)
    rng = np.random.default_rng(7)
    masa_testi(rng)
    refs = [vakum_denemesi(i, rng) for i in (1, 2, 3)]
    with open(KLASOR / "vakum_referans.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=refs[0].keys())
        w.writeheader()
        w.writerows(refs)
    bilgi = ucus(rng)
    with open(KLASOR / "ucus_referans.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=bilgi.keys())
        w.writeheader()
        w.writerow(bilgi)
    ateslemeler()
    print("örnek veriler veri/ klasörüne yazıldı")


if __name__ == "__main__":
    main()
