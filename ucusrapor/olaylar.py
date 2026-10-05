"""Uçuş bittikten sonra bütün kayda bakarak bulunan referans olaylar.

Algoritmaların başarısını ölçmek için tepe noktasının gerçek anını bilmek
gerekiyor. Uçuş sırasında sadece geçmişe bakılabilir, ama uçuştan sonra
kaydın tamamı elimizde: irtifayı hem önceki hem sonraki örneklerle
filtreleyip en yüksek noktayı bulabiliyoruz. Bu sonuç, kulübün her uçuş
için bildirdiği tepe irtifasıyla birkaç metre içinde uyuşuyor
(docs/sonuclar.md).
"""
import numpy as np
import pandas as pd

from ucusrapor.algoritmalar import ARDISIK, BITIS_G, KALKIS_G
from ucusrapor.okuma import HZ, irtifa


def kalkis_indeksi(ivme):
    i = np.flatnonzero(np.asarray(ivme) > KALKIS_G)
    if len(i) == 0:
        raise ValueError("kayıtta kalkış yok (ivme hiç 3 g'yi geçmiyor)")
    return int(i[0])


def olaylar(d):
    """kalkis_s, motor_bitisi_s, tepe_s, tepe_m ve filtrelenmiş irtifa dizisi."""
    t, a = d["t_s"].to_numpy(), d["ivme_g"].to_numpy()
    k = kalkis_indeksi(a)
    p0 = d["basinc_pa"].iloc[:k].mean()
    # 1 s'lik ortalanmış medyan: tek örneklik sensör sıçramalarını siler, tepeyi kaydırmaz
    h = pd.Series(irtifa(d["basinc_pa"], p0)).rolling(int(HZ), center=True, min_periods=1).median().to_numpy().copy()
    h[:k] = 0.0

    bitis = None
    altinda = (a < BITIS_G) & (np.arange(len(a)) > k)
    for i in range(k, len(a)):
        if i - ARDISIK + 1 > k and altinda[i - ARDISIK + 1:i + 1].all():
            bitis = float(t[i])
            break

    i_tepe = int(np.argmax(h))
    return {"kalkis_s": float(t[k]), "motor_bitisi_s": bitis,
            "tepe_s": float(t[i_tepe]), "tepe_m": float(h[i_tepe]), "irtifa_m": h}
