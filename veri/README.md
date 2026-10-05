# Veri

Bu klasördeki uçuş kayıtları NC State University High-Powered Rocketry
Club'ın [AirbrakesV2](https://github.com/NCSU-High-Powered-Rocketry-Club/AirbrakesV2)
reposundan alındı. Kulüp, hava freni yazılımını geliştirirken kendi
roketlerinin gerçek uçuş kayıtlarını bu repoda paylaşıyor. Veriler MIT
lisansıyla yayımlanmış.

`ucuslar.csv` dosyasında her uçuşun tarihi, yeri, kullanılan sensör,
kulübün bildirdiği tepe irtifası ve kaydın repodaki tam yolu (commit dahil)
var. "not" sütununu kulübün kendi uçuş açıklamalarından kısaltarak yazdım.

`ucuslar/` altındaki her dosya bir uçuş. Ham kayıtları `veri_hazirla.py`
şu şekilde dönüştürüyor:

| sütun | birim | anlamı |
|---|---|---|
| `t_s` | s | kesitin başından geçen süre |
| `basinc_pa` | Pa | barometrik basınç |
| `ivme_g` | g | roketin ekseni boyunca ivme |
| `ncsu_durum` | | kulübün uçuş yazılımının o anki durumu |

Ham kayıtlarda sensör saniyede 100 ile 1500 arasında örnek alıyor. Hepsini
saniyede 50 örneğe getirdim; her an için o ana kadar gelen son ölçümü
kullandım. Kartlar rokete farklı yönlerde monte edildiği için ivmeyi,
rampada ölçülen yerçekimi yönüne, yani roketin eksenine izdüşürdüm. Her
dosya kalkıştan 5 saniye önce başlıyor ve en fazla 120 saniye sürüyor.

`ncsu_durum` sütunundaki harfler kulübün uçuş yazılımının durumları: S
rampada bekleme, M motor yanıyor, C süzülme, F serbest düşüş (tepe noktası
geçildi), L iniş. Raporda kulübün tepe noktası kararı olarak, motor
başladıktan sonra F'ye ilk geçtiği an kullanılıyor.

Kulübün reposundaki iki uçuşu daha (`purple_launch`, `shake_n_bake`)
almadım, çünkü bu kayıtlarda ham basınç yok ve birine sonradan üretilmiş
iniş verisi eklenmiş. `legacy_launch_2` kaydında da uçuş yok.
`pelicanator_launch_3` uçuşunun kaydı SD kart bozulduğu için hiç yok;
`lil_frank` ve `government_work_2_scrubbed` ise iptal edilip uçmamış.

`government_work_1` için kulübün zaman damgalarını düzelttiği
`government_work_1_time_fix.csv` dosyasını kullandım. `government_work_2`
uçuşunun tarihi kulübün listesinde 2025-02-07 yazıyor, ama kayıttaki zaman
damgaları 7 Şubat 2026'yı gösteriyor; tabloya 2026 olarak yazdım.

Ham kayıtları indirip tabloları baştan üretmek için:

```
python veri_hazirla.py
```
