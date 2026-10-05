/*
 * Bilgisayarda test için: uçuş kaydını (CSV, ilk üç sütun t_s, basinc_pa,
 * ivme_g, ilk satır başlık) stdin'den okur, her satırı tepe_adim()'a verir
 * ve paraşüt komutunun verildiği anı yazar.
 *
 *   tepe_cli < veri/ucuslar/jackpot_launch_2.csv
 */
#include <stdio.h>

#include "tepe.h"

int main(void)
{
    char satir[256];
    if (!fgets(satir, sizeof(satir), stdin))
        return 1; /* başlık */

    tepe_durum_t d;
    tepe_baslat(&d);
    float t, p, a;
    while (fgets(satir, sizeof(satir), stdin)) {
        if (sscanf(satir, "%f,%f,%f", &t, &p, &a) != 3) {
            fprintf(stderr, "bozuk satır: %s", satir);
            return 1;
        }
        if (tepe_adim(&d, t, p, a)) {
            printf("%.2f\n", (double)t);
            return 0;
        }
    }
    printf("yok\n");
    return 0;
}
