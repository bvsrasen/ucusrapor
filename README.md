# UçuşRapor

TEKNOFEST Orta İrtifa'da yarışan ÇGM AKANA Rocket Team'de aviyonik
yazılımında çalışıyorum. Atışımızda paraşüt açılmadı. Kurtarmayı büyük
ölçüde ticari uçuş bilgisayarına bırakmıştık ve o kartın rampada yer
istasyonuyla bağlantısı kurulamadı. Uçuş sırasında yer istasyonundan
izlediğimiz telemetride, kendi kartımızın basınç verisinin roket ses hızını
geçerken bozulduğunu da gördük. Tepe noktasını basınca bakarak bulan
algoritmamız o hâliyle paraşütü yanlış zamanda açabilirdi. Ne yazık ki bu
veriyi sadece ekrandan izledik ve kaydetmedik, bu yüzden sonradan
inceleyemedik.

Bu proje o atıştan kalan soruyu gerçek verilerle cevaplamaya çalışıyor:
basınca dayalı paraşüt açma algoritmaları gerçek uçuşlarda ne zaman
yanılıyor, ve bunu önlemenin uçuş bilgisayarına kolayca konabilecek basit
bir yolu var mı? Kendi kaydımız olmadığı için, NC State Üniversitesi roket
kulübünün açık olarak paylaştığı 12 gerçek uçuş kaydını kullandım.

Çıkan sonuç şu: bizim kartımızdaki gibi "en yüksek değerden 3 metre düşünce
paraşütü aç" diyen basit kural, 12 uçuşun 5'inde paraşütü tepe noktasından 5
ile 12,5 saniye önce, yani roket hâlâ hızla yükselirken açıyor. Motorun
bittiğini ivmeölçerden anlayıp basınca ancak bir saniye sonra bakmaya
başlayan ve basıncı medyan filtreden geçiren bir sürüm ise 12 uçuşun
hepsinde paraşütü tepe noktasından 0,9 ila 1,7 saniye sonra açıyor. Bu
algoritmanın C hâlini de yazdım; STM32'ye doğrudan konabilecek kadar küçük.

![jackpot_launch_2 uçuşu](docs/jackpot_launch_2.png)

Bu grafik, en çarpıcı örnek olan `jackpot_launch_2` uçuşunu gösteriyor.
Motor yaklaşık 3. saniyede bitiyor ve tam o anda basınç sensörü bir anda
yükseliyor: basınçtan hesaplanan irtifa iki ölçüm arasında yaklaşık 265
metreden -200 metreye düşüyor. Kulübün notuna göre bu uçuşta hava frenlerinin
bölmesi içeriden sızdırmaz değilmiş ve frenler açılınca büyük bir basınç
sıçraması olmuş. Basit kural bu düşüşü "tepeyi geçtik" diye yorumlayıp
paraşüt komutunu roket tepeye çıkmadan 11,8 saniye önce veriyor. Önerdiğim
algoritma ise bu sırada barometreye bakmadığı için komutu tepeden 1,5 saniye
sonra veriyor.

## Veri

Kullandığım kayıtlar NCSU High-Powered Rocketry Club'ın
[AirbrakesV2](https://github.com/NCSU-High-Powered-Rocketry-Club/AirbrakesV2)
reposundan geliyor. Kulüp, 2024-2026 arasında yaptığı uçuşların ham sensör
kayıtlarını bu repoda paylaşıyor. Uçuşlar 460 ile 1400 metre arasına
çıkıyor. Her kayıtta barometrik basınç, üç eksenli ivme ve
kulübün kendi uçuş yazılımının o anki durumu var. Kulüp ayrıca her uçuş için
ulaşılan tepe irtifasını bildirmiş.

Ham kayıtlar yaklaşık 200 MB olduğu için repoya koymadım. `veri_hazirla.py`
onları belirli commit'lerden indirip saniyede 50 örneklik tablolara
çeviriyor ve uçuş kısmını kesip `veri/ucuslar/` klasörüne yazıyor. Bu
tablolar toplam 1 MB ve repoda duruyor, yani analizi çalıştırmak için bir şey
indirmek gerekmiyor. Ayrıntıları [veri/README.md](veri/README.md) dosyasında
anlattım.

## Nasıl çalışıyor

Bütün algoritmalar bir uçuş bilgisayarı gibi örnek örnek çalışıyor. Her
adımda sadece o ana kadar gelen ölçümleri görüyorlar ve paraşüt komutunu
verdikleri anı döndürüyorlar. Hepsinde ortak olan kısım şu: roket rampada
beklerken basıncın ortalaması alınıyor, ivme 3 g'yi geçince kalkış kabul
ediliyor ve o ortalama rampa basıncı oluyor. İrtifa her adımda bu rampa
basıncına göre standart atmosfer formülüyle hesaplanıyor.

Karşılaştırdığım algoritmalar şunlar:

| algoritma | ne yapıyor |
|---|---|
| Basit barometrik | En yüksek irtifanın 3 m altında art arda 5 ölçüm görünce paraşütü açar. Bizim kartımızdaki mantık buydu. |
| Ortalama filtreli | Aynı kural, irtifanın son 0,5 saniyelik ortalamasıyla. |
| Medyan filtreli | Aynı kural, irtifanın son 0,5 saniyelik medyanıyla. Medyan, tek tek sıçrayan ölçümlerden ortalamaya göre daha az etkilenir. |
| Hız işareti | İrtifadan hesaplanan dikey hız 0,5 saniye boyunca negatif kalınca açar. |
| Motor kilidi + basit | Motorun bittiğini ivmeden anlar (ivme art arda 5 ölçüm negatif), ondan sonraki 1 saniye basınca hiç bakmaz, sonra basit kuralı uygular. |
| Motor kilidi + medyan | Motor kilidi ile medyan filtrenin birlikte kullanıldığı sürüm. Önerdiğim algoritma bu. |

Bunlara ek olarak NCSU'nun kendi uçuş yazılımının uçuş sırasında verdiği
kararı da karşılaştırmaya kattım. Kulübün yazılımı tepe noktasını geçtiğine
karar verdiğinde kayda "F" (serbest düşüş) yazıyor.

Motor bitince roket hava direnciyle yavaşladığı için, roketin ekseni boyunca
ölçülen ivme negatife düşüyor. Kartlar rokete farklı yönlerde monte edildiği
için ivmeyi, rampada ölçülen yerçekimi yönüne, yani roketin eksenine
izdüşürdüm. Bu sayede motor bitişi her uçuşta kalkıştan 1,3 ile 3,0 saniye
sonra bulunuyor.

## Gerçek tepe noktası

Bir algoritmanın erken ya da geç kaldığını söyleyebilmek için tepe
noktasının gerçek anını bilmek gerekiyor. Uçuş sırasında sadece geçmişe
bakılabilir, ama uçuş bittikten sonra kaydın tamamı elimizde. Bu yüzden
irtifayı hem önceki hem sonraki ölçümlere bakan 1 saniyelik bir medyan
filtreden geçirip en yüksek noktayı buldum. Bu şekilde bulunan tepe
irtifası, kulübün bildirdiği değerle 12 uçuşun hepsinde en fazla 6 metre
farkla uyuşuyor. Örneğin `jackpot_launch_4`, kulübün NASA Student Launch
yarışmasında 1404 metreye (4606 ft) çıkıp irtifa ödülünü aldığı uçuş;
burada bulunan değer 1408 metre.

Tepe noktasında roketin dikey hızı sıfır. Bir saniye önce roket hâlâ
yaklaşık 10 m/s ile yükseliyor, iki saniye sonra ise yaklaşık 20 m/s ile
düşüyor. Bu yüzden paraşüt komutu tepeden en fazla 1 saniye önce ya da en
fazla 2 saniye sonra verildiyse "zamanında" saydım.

## Sonuçlar

| algoritma | zamanında | erken | geç | en erken | en geç |
|---|---|---|---|---|---|
| Basit barometrik | 7 | 5 | 0 | -12,5 s | +1,3 s |
| Ortalama filtreli | 9 | 3 | 0 | -12,4 s | +1,7 s |
| Medyan filtreli | 9 | 3 | 0 | -12,2 s | +1,7 s |
| Hız işareti | 10 | 2 | 0 | -11,3 s | +1,3 s |
| Motor kilidi + basit | 11 | 1 | 0 | -5,2 s | +1,3 s |
| **Motor kilidi + medyan** | **12** | **0** | **0** | **+0,9 s** | **+1,7 s** |
| NCSU uçuş yazılımı | 9 | 0 | 3 | -0,3 s | +6,8 s |

![Gecikmeler](docs/gecikmeler.png)

Basit kuralın erken açtığı beş uçuşun dördünde komut, motor bitişinden en
fazla yarım saniye sonra veriliyor. Bu uçuşlarda basınç sensörü motor
bitişinde kısa bir süre bozuk ölçüyor. Kulübün notlarına göre bu
uçuşların bazılarında hava frenleri süzülmenin hemen başında açılmış, bu
yüzden bozulmanın büyük ihtimalle frenlerden geldiğini düşünüyorum.
Beşinci uçuş olan `pelicanator_launch_1`'de ise basınçtaki sıçrama
süzülmenin ortasında, kalkıştan 10 saniye sonra oluyor.

Filtre eklemek bazı uçuşlarda işe yarıyor, ama bozulma yarım saniyeden uzun
sürdüğünde filtre de onu gerçek bir değişim sanıyor. Motor kilidi ise
sorunun büyük kısmını kökünden çözüyor, çünkü basınç tam da en güvenilmez
olduğu anda hiç dinlenmiyor. Kilit tek başına yetmiyor; `pelicanator_launch_1`
uçuşundaki sıçrama kilit bittikten sonra geliyor ve onu medyan filtre
temizliyor.

NCSU'nun kendi yazılımı hiçbir uçuşta erken karar vermemiş, ama üç uçuşta
tepeyi 4,5 ila 6,8 saniye geç fark etmiş. O anlarda roket tepeden 60 ile 135
metre kadar düşmüş oluyor. Kulübün yazılımı paraşütü açmıyor, bu kararı hava
frenlerini kapatmak için kullanıyor; paraşütler ayrı bir sistemle açılıyor.
Yine de aynı karar bir uçuş bilgisayarında paraşüt komutu olarak
kullanılsaydı, paraşüt hızlanmış bir rokette açılır ve hem paraşütü hem
roketi zorlardı.

Önerdiğim algoritmayı bu 12 uçuşa bakarak seçtiğim için sonucu biraz iyimser
görmek gerekiyor. Parametrelere aşırı bağlı olup olmadığını görmek için
motor kilidi süresini 0,5 ile 2 saniye, medyan penceresini 0,3 ile 1 saniye
arasında değiştirdim. Kilit süresi sonucu hiç değiştirmiyor; medyan
penceresi 1 saniyeye çıkınca iki uçuşta komut 2 saniyeden biraz fazla
gecikiyor. Bütün tablolar ve uçuş uçuş sonuçlar
[docs/sonuclar.md](docs/sonuclar.md) dosyasında.

## C kodu

Önerilen algoritmanın C hâli `c/tepe.h` ve `c/tepe.c` dosyalarında. Kod
dinamik bellek kullanmıyor ve 32 bitlik kayan nokta sayılarla çalışıyor.
Uçuş bilgisayarının ana döngüsünde her ölçümde bir kez `tepe_adim()`
çağrılıyor:

```c
static tepe_durum_t tepe;

tepe_baslat(&tepe);

/* saniyede 50 kez */
if (tepe_adim(&tepe, t_s, basinc_pa, ivme_g)) {
    /* paraşüt komutu */
}
```

Sensörden bozuk bir değer (NaN ya da sonsuz) gelirse o ölçüm atlanıyor;
böylece tek bir bozuk okuma rampa basıncını ya da filtreyi bozamıyor.
Cortex-M4 için derlendiğinde kod 480 bayt yer kaplıyor. C kodunu kontrol
etmek için `c/tepe_cli` adlı küçük bir program yazdım. Bu program bir
uçuş kaydını okuyup C fonksiyonuna veriyor. 12 uçuşun hepsinde C kodu
paraşüt komutunu Python ile aynı örnekte veriyor; bu kontrol testlerin
içinde de var.

## Kendi kaydınızla kullanmak

Kendi uçuş bilgisayarınızın kaydını da aynı şekilde inceleyebilirsiniz.
Kaydın `t_s` (saniye), `basinc_pa` (Pa) ve `ivme_g` (roketin ekseni boyunca,
g) sütunları olan bir CSV dosyası olması yeterli:

```
python ucusrapor.py --kayit ucusumuz.csv
```

Bu komut her algoritmanın paraşüt komutunu ne zaman verdiğini yazıyor ve
`rapor/` klasörüne bir grafik çiziyor. Kayıt saniyede 50 örnekten farklı bir
hızdaysa otomatik olarak bu hıza getiriliyor.

## Çalıştırma

Python 3.11 ya da daha yeni bir sürüm, C tarafı için de gcc ve make
gerekiyor.

```
pip install -r requirements.txt
python -m pytest           # testler
python ucusrapor.py        # 12 uçuşu değerlendirir, rapor/ucusrapor.xlsx ve docs/ altındaki dosyaları üretir
make -C c                  # C kodunu derler
python veri_hazirla.py     # isteğe bağlı: ham kayıtları indirip tabloları baştan üretir
```

GitHub'a her gönderimde testler çalışıyor, C kodu derleniyor ve
`docs/sonuclar.md` baştan üretilip repodaki hâliyle karşılaştırılıyor.

## Eksikler

Bu uçuşların hiçbiri ses hızına ulaşmıyor. En yüksek tepe irtifası 1,4 km;
ses hızına ulaşan bir roket motor bittikten sonra bundan çok daha yükseğe
çıkardı. Bu yüzden bizim atışımızdaki gibi ses hızı civarında oluşan basınç
bozulması burada yok; buradaki bozulmalar motor bitişinden ve hava
frenlerinden geliyor. Motor kilidi ses hızı bozulmasına karşı da işe
yarayacak gibi görünüyor, çünkü roket ses hızını motor yanarken ya da hemen
sonrasında geçer. Ama bunu ancak kendi uçuş kayıtlarımızla doğrulayabiliriz.
Bir sonraki atışımızda kartın ham basınç ve ivme verisini SD karta
kaydetmeyi planlıyorum.

12 uçuş az bir sayı ve hepsi aynı kulübün roketlerinden geliyor. Algoritmayı
henüz gerçek bir STM32 kartında çalıştırmadım. İvmeölçer bozulursa motor
kilidi hiç açılmayabilir; uçuş bilgisayarında buna karşı bir zamanlayıcı
yedeği olması gerekiyor.

## Kaynak

Uçuş kayıtları: NCSU High-Powered Rocketry Club,
[AirbrakesV2](https://github.com/NCSU-High-Powered-Rocketry-Club/AirbrakesV2),
MIT lisansı. Hangi dosyanın hangi commit'ten alındığı
[veri/ucuslar.csv](veri/ucuslar.csv) dosyasında yazıyor.

---

Büşra Şen · İstanbul Medipol Üniversitesi, Yönetim Bilişim Sistemleri
