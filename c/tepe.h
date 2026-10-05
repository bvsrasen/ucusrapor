/*
 * Paraşüt açma (tepe noktası) tespiti, ucusrapor/algoritmalar.py'deki
 * "Motor kilidi + medyan" algoritmasının C hâli.
 *
 * Saniyede 50 kez tepe_adim() çağrılır. Dinamik bellek yok.
 *   1. Rampada basınç ortalaması alınır; eksenel ivme 3 g'yi geçince kalkış.
 *   2. Eksenel ivme art arda 5 örnek negatif olunca motor bitmiştir; ondan
 *      sonraki 1 s barometreye bakılmaz.
 *   3. İrtifa son 0,5 s'nin medyanıyla filtrelenir. En yüksek değerin 3 m
 *      altında art arda 5 örnek görülünce paraşüt komutu verilir.
 *
 * Bozuk bir ölçüm (NaN ya da sonsuz) gelirse o örnek atlanır.
 */
#ifndef TEPE_H
#define TEPE_H

#define TEPE_PENCERE 25 /* 0,5 s */

typedef struct {
    float p_ort;        /* rampa basıncı ortalaması (Pa) */
    long p_sayi;
    int kalkti;
    float gecmis[TEPE_PENCERE]; /* son irtifalar, halka tampon */
    int n_gecmis, i_gecmis;
    int bitis_sayac;
    int motor_bitti;
    float dinleme_basi; /* barometreye bakılmaya başlanacak an (s) */
    float en_yuksek;
    int sayac;
    int acildi;
} tepe_durum_t;

void tepe_baslat(tepe_durum_t *d);

/* Paraşüt komutunun verilmesi gereken örnekte 1, diğerlerinde 0 döner. */
int tepe_adim(tepe_durum_t *d, float t_s, float basinc_pa, float ivme_g);

#endif
