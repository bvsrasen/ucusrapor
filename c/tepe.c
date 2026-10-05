#include "tepe.h"

#include <math.h>
#include <string.h>

#define KALKIS_G 3.0f
#define BITIS_G 0.0f
#define ARDISIK 5
#define DUSUS_M 3.0f
#define KILIT_S 1.0f

void tepe_baslat(tepe_durum_t *d)
{
    memset(d, 0, sizeof(*d));
    d->en_yuksek = -INFINITY;
}

static float irtifa(float p, float p0)
{
    return 44330.0f * (1.0f - powf(p / p0, 0.190263f));
}

/* Halka tampondaki irtifaların medyanı (çift sayıda örnekte ortadaki ikisinin ortalaması) */
static float medyan(const tepe_durum_t *d)
{
    float s[TEPE_PENCERE];
    int n = d->n_gecmis;
    memcpy(s, d->gecmis, (size_t)n * sizeof(float));
    for (int i = 1; i < n; i++) {
        float x = s[i];
        int j = i - 1;
        while (j >= 0 && s[j] > x) {
            s[j + 1] = s[j];
            j--;
        }
        s[j + 1] = x;
    }
    return (n % 2) ? s[n / 2] : 0.5f * (s[n / 2 - 1] + s[n / 2]);
}

int tepe_adim(tepe_durum_t *d, float t_s, float basinc_pa, float ivme_g)
{
    if (d->acildi)
        return 0;
    /* Bozuk ölçüm (NaN ya da sonsuz) hiç gelmemiş gibi atlanır */
    if (!isfinite(t_s) || !isfinite(basinc_pa) || !isfinite(ivme_g))
        return 0;

    if (!d->kalkti) {
        if (ivme_g > KALKIS_G && d->p_sayi > 0) {
            d->kalkti = 1;
        } else {
            d->p_sayi++;
            d->p_ort += (basinc_pa - d->p_ort) / (float)d->p_sayi;
            return 0;
        }
    }

    d->gecmis[d->i_gecmis] = irtifa(basinc_pa, d->p_ort);
    d->i_gecmis = (d->i_gecmis + 1) % TEPE_PENCERE;
    if (d->n_gecmis < TEPE_PENCERE)
        d->n_gecmis++;
    float h = medyan(d);

    if (!d->motor_bitti) {
        d->bitis_sayac = (ivme_g < BITIS_G) ? d->bitis_sayac + 1 : 0;
        if (d->bitis_sayac >= ARDISIK) {
            d->motor_bitti = 1;
            d->dinleme_basi = t_s + KILIT_S;
        }
        return 0;
    }
    if (t_s < d->dinleme_basi)
        return 0;

    if (h > d->en_yuksek) {
        d->en_yuksek = h;
        d->sayac = 0;
    } else if (h < d->en_yuksek - DUSUS_M) {
        if (++d->sayac >= ARDISIK) {
            d->acildi = 1;
            return 1;
        }
    } else {
        d->sayac = 0;
    }
    return 0;
}
