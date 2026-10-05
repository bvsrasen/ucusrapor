"""Tepe noktası (paraşüt açma) algoritmaları.

Hepsi bir uçuş bilgisayarındaki gibi örnek örnek çalışıyor: sadece o ana
kadar gelen ölçümleri görüyor ve paraşüt komutunu verdiği anı döndürüyor.
Örnek sayıları 50 Hz'e göre (25 örnek = 0,5 s).

Ortak adımlar:
- Rampada beklerken basınç ortalaması alınıyor; eksenel ivme 3 g'yi geçince
  kalkış kabul ediliyor ve o ortalama rampa basıncı oluyor.
- İrtifa, rampa basıncına göre standart atmosfer formülüyle hesaplanıyor.
- Tepe kuralı: o ana kadarki en yüksek irtifanın 3 m altında art arda 5
  örnek görülünce paraşüt açılıyor.
"""
import numpy as np

from ucusrapor.okuma import HZ, irtifa

KALKIS_G = 3.0      # bu ivmenin üstü kalkış
BITIS_G = 0.0       # kalkıştan sonra eksenel ivme negatife düşünce motor bitmiştir (hava direnci)
ARDISIK = 5         # bir koşulun art arda tutması gereken örnek sayısı
DUSUS_M = 3.0       # en yüksek irtifadan bu kadar düşüş tepeyi geçtik demek
PENCERE = 25        # filtre penceresi, 0,5 s
KILIT_S = 1.0       # motor bitişinden sonra barometreyi dinlememe süresi


def tepe_bul(t, basinc, ivme, filtre=None, kilit=False, pencere=PENCERE, kilit_s=KILIT_S):
    """Paraşüt komutunun verildiği an (s); hiç verilmezse None.

    filtre: None, "ortalama" ya da "medyan" (son `pencere` örneğin irtifaları)
    kilit:  True ise motor bitişi ivmeden anlaşılıyor (eksenel ivme art arda 5
            örnek negatif) ve ondan sonraki `kilit_s` saniye boyunca
            barometreye bakılmıyor. Motor yanarken ve hemen sonrasında basınç
            ölçümü bozulabiliyor.
    """
    p_ort, p_sayi, kalkti = 0.0, 0, False
    gecmis = []
    bitis_sayac, dinleme_basi = 0, None
    en_yuksek, sayac = -np.inf, 0

    for ti, pi, ai in zip(t, basinc, ivme):
        if not (np.isfinite(ti) and np.isfinite(pi) and np.isfinite(ai)):
            continue  # bozuk ölçüm hiç gelmemiş gibi atlanıyor
        if not kalkti:
            if ai > KALKIS_G and p_sayi > 0:
                kalkti = True
            else:
                # Rampa basıncının ortalaması, her örnekte güncelleniyor
                p_sayi += 1
                p_ort += (pi - p_ort) / p_sayi
                continue

        h = float(irtifa(pi, p_ort))
        gecmis.append(h)
        if len(gecmis) > pencere:
            gecmis.pop(0)
        if filtre == "ortalama":
            h = float(np.mean(gecmis))
        elif filtre == "medyan":
            h = float(np.median(gecmis))

        if kilit:
            if dinleme_basi is None:
                bitis_sayac = bitis_sayac + 1 if ai < BITIS_G else 0
                if bitis_sayac >= ARDISIK:
                    dinleme_basi = ti + kilit_s
                continue
            if ti < dinleme_basi:
                continue

        if h > en_yuksek:
            en_yuksek, sayac = h, 0
        elif h < en_yuksek - DUSUS_M:
            sayac += 1
            if sayac >= ARDISIK:
                return float(ti)
        else:
            sayac = 0
    return None


def hiz_isareti(t, basinc, ivme):
    """Dikey hız 0,5 s boyunca negatif kalınca paraşüt açılır.

    Hız, son 0,5 s'nin ortalama irtifasıyla ondan önceki 0,5 s'nin ortalama
    irtifası arasındaki farktan hesaplanıyor.
    """
    p_ort, p_sayi, kalkti = 0.0, 0, False
    gecmis, sayac = [], 0
    for ti, pi, ai in zip(t, basinc, ivme):
        if not (np.isfinite(ti) and np.isfinite(pi) and np.isfinite(ai)):
            continue
        if not kalkti:
            if ai > KALKIS_G and p_sayi > 0:
                kalkti = True
            else:
                p_sayi += 1
                p_ort += (pi - p_ort) / p_sayi
                continue
        gecmis.append(float(irtifa(pi, p_ort)))
        if len(gecmis) > 2 * PENCERE:
            gecmis.pop(0)
        if len(gecmis) < 2 * PENCERE:
            continue
        hiz = (np.mean(gecmis[PENCERE:]) - np.mean(gecmis[:PENCERE])) / (PENCERE / HZ)
        sayac = sayac + 1 if hiz < 0 else 0
        if sayac >= PENCERE:
            return float(ti)
    return None


def ncsu_karari(t, durum):
    """NCSU uçuş yazılımının serbest düşüşe (F) geçtiği an: motor (M) başladıktan sonraki ilk F."""
    durum = np.asarray(durum)
    motor = np.flatnonzero(durum == "M")
    if len(motor) == 0:
        return None
    f = np.flatnonzero((durum == "F") & (np.arange(len(durum)) > motor[0]))
    return float(np.asarray(t)[f[0]]) if len(f) else None


# Rapordaki sıra; ilki takımımızın kartındaki kural, sonuncusu önerdiğim
ALGORITMALAR = {
    "Basit barometrik": lambda d: tepe_bul(d.t_s, d.basinc_pa, d.ivme_g),
    "Ortalama filtreli": lambda d: tepe_bul(d.t_s, d.basinc_pa, d.ivme_g, filtre="ortalama"),
    "Medyan filtreli": lambda d: tepe_bul(d.t_s, d.basinc_pa, d.ivme_g, filtre="medyan"),
    "Hız işareti": lambda d: hiz_isareti(d.t_s, d.basinc_pa, d.ivme_g),
    "Motor kilidi + basit": lambda d: tepe_bul(d.t_s, d.basinc_pa, d.ivme_g, kilit=True),
    "Motor kilidi + medyan": lambda d: tepe_bul(d.t_s, d.basinc_pa, d.ivme_g, filtre="medyan", kilit=True),
}
ONERILEN = "Motor kilidi + medyan"
