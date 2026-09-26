"""Farklı tepe noktası (apogee) tespit yöntemleri.

Hepsi aynı veriyle çalışıp tespit anını döndürüyor, böylece hangisinin ne zaman
ve neden yanıldığını yan yana görebiliyoruz.
"""
import numpy as np

G = 9.80665


def basit_barometrik(t, h, dusus_m=3.0, ardisik=5):
    """En yüksek değerden `dusus_m` kadar aşağıda art arda `ardisik` örnek görülünce tetikler.

    Özgün kartta kullandığımız mantığa benziyor. Basınç ölçümü dalgalanırsa
    (vakum pompası, ses hızı civarı) erken tetikleyebiliyor.
    """
    en_yuksek, sayac = -np.inf, 0
    for ti, hi in zip(t, h):
        if hi > en_yuksek:
            en_yuksek, sayac = hi, 0
        elif hi < en_yuksek - dusus_m:
            sayac += 1
            if sayac >= ardisik:
                return float(ti)
        else:
            sayac = 0
    return None


def filtreli_barometrik(t, h, pencere=25, **kw):
    """Aynı mantık, önce hareketli ortalama uygulanarak."""
    h = np.asarray(h, dtype=float)
    hf = np.convolve(h, np.ones(pencere) / pencere, mode="same")
    yarim = pencere // 2
    hf[:yarim] = h[:yarim]
    hf[-yarim:] = h[-yarim:]
    return basit_barometrik(t, hf, **kw)


def ivmeden_hiz(t, az_g, kalkis_s):
    """Eksenel ivmeyi integre ederek dikey hız tahmini (m/s)."""
    v = np.zeros(len(t))
    for i in range(1, len(t)):
        a = (az_g[i] - 1.0) * G if t[i] >= kalkis_s else 0.0
        v[i] = v[i - 1] + a * (t[i] - t[i - 1])
    return v


def ivme_entegrasyonu(t, az_g, kalkis_s):
    """Tahmini hızın sıfırın altına düştüğü an."""
    v = ivmeden_hiz(t, az_g, kalkis_s)
    for i in np.where(t > kalkis_s + 1)[0]:
        if v[i] <= 0:
            return float(t[i])
    return None


def mach_kilitli_barometrik(t, h, az_g, kalkis_s, kilit_hizi=200.0, **kw):
    """Tahmini hız `kilit_hizi` m/s'nin üzerindeyken barometreyi dinlemez.

    Ses hızı civarında statik basınç ölçümü güvenilir olmadığı için kilit
    açılana kadar tepe noktası aranmıyor.
    """
    t = np.asarray(t)
    v = ivmeden_hiz(t, az_g, kalkis_s)
    acik = (t > kalkis_s + 1) & (v < kilit_hizi)
    if not acik.any():
        return None
    ilk = int(np.argmax(acik))
    return filtreli_barometrik(t[ilk:], np.asarray(h)[ilk:], **kw)


def zaman_kilitli_barometrik(t, h, kalkis_s, kilit_s=10.0, **kw):
    """Kalkıştan sonraki ilk `kilit_s` saniye barometreyi dinlemez.

    İvmeölçer ±16 g'de doyuma girdiği için ivmeden hız tahmini düşük çıkıyor
    ve Mach kilidi erken açılıyor. Süreyi uçuş simülasyonundan (transonik
    bölgenin bittiği an + pay) seçmek daha güvenli.
    """
    t, h = np.asarray(t), np.asarray(h)
    m = t > kalkis_s + kilit_s
    return filtreli_barometrik(t[m], h[m], **kw)


def hepsini_dene(df, kalkis_s, zamanlayici_s):
    t, h, az = df["t_s"].to_numpy(), df["irtifa_m"].to_numpy(), df["az_g"].to_numpy()
    return {
        "Basit barometrik (mevcut)": basit_barometrik(t, h),
        "Filtreli barometrik": filtreli_barometrik(t, h),
        "İvme entegrasyonu": ivme_entegrasyonu(t, az, kalkis_s),
        "Mach kilitli + filtreli barometrik": mach_kilitli_barometrik(t, h, az, kalkis_s),
        "Zaman kilitli + filtreli barometrik": zaman_kilitli_barometrik(t, h, kalkis_s),
        "Zamanlayıcı (simülasyondan)": kalkis_s + zamanlayici_s,
    }
