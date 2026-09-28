# UçuşRapor

TEKNOFEST Orta İrtifa'da yarışan ÇGM AKANA Rocket Team'de aviyonik yazılımında çalıştım. Atıştan önce vakumlama, yer ateşleme ve masa testleri yaptık ama testlerde veriyi sadece ekrandan izledik, hiçbirini kaydetmedik. Özgün uçuş bilgisayarımızla (STM32) ticari uçuş bilgisayarını hiçbir zaman aynı test üzerinden yan yana koyup karşılaştırmadık.

Sonuçta kurtarmayı neredeyse tamamen ticari karta bıraktık. Atışta ticari kartın rampada yer istasyonuyla bağlantısı kurulamadı (büyük ihtimalle hakem altimetresi takılırken bir kablo temassızlık yaptı) ve paraşüt açılmadı. Uçuş sırasında özgün kartın basınç verisinin, roket ses hızını geçerken bozulduğunu gördük; yani bizim algoritmamız da o hâliyle tepe noktasını doğru bulamayacaktı.

Geriye dönüp baktığımda asıl eksik şuydu: testleri kaydedip iki kartı karşılaştırsaydık bu sorunların çoğunu yerde görebilir, başka bir ayırma yöntemine (ya da yedek bir tetikleme mantığına) karar verebilirdik.

Bu repo o eksiği kapatmak için yazdığım küçük bir araç. İki kartın test kayıtlarını okuyor, temizliyor, saatlerini hizalıyor ve tepe noktası tespitini farklı yöntemlerle karşılaştırıp bir Excel raporu çıkarıyor.

![Rapor örneği](docs/rapor_ornegi.png)

## Ne yapıyor?

- Özgün kartın SD kayıtlarındaki bozuk / yarım satırları, kopya satırları, sensörün 0 ya da takılı döndüğü okumaları ve kayıt boşluklarını buluyor
- Ticari kartın kaydını, irtifa eğrileri üst üste gelecek şekilde kaydırarak özgün kartın saatine hizalıyor (iki kartın saati senkron değil)
- Masa testinde gürültü ve kaymayı, vakum odası testinde iki kartın tepe noktasını ne zaman bulduğunu karşılaştırıyor
- Uçuş verisi üzerinde birkaç tepe noktası yöntemini deniyor: mevcut basit barometrik, filtreli, ivme entegrasyonu, Mach kilitli, zaman kilitli ve zamanlayıcı
- Yer ateşleme testlerinde tuttuğumuz formu rapora ekliyor

## Örnek veri

Gerçek kayıtlarımız olmadığı için `veri_uret.py` ile örnek veri ürettim ve aracı bununla geliştirdim. **`veri/` klasöründeki dosyalar gerçek test ya da uçuş kaydı değil.** Örnek veriyi olabildiğince gerçekçi yapmaya çalıştım:

- uçuş profili Orta İrtifa sınıfına göre (~3 km tepe noktası, yanma sonunda ~Mach 1,1), ses hızı civarında statik basınç hatası var
- ivmeölçer ±16 g'de doyuma giriyor
- SD kartta yazma gecikmesi kaynaklı boşluklar, kopya satırlar, güç kesilince yarım kalan son satır
- basınç sensörünün ara ara 0 döndürmesi ya da birkaç örnek aynı değerde takılı kalması
- kart ısındıkça basınç sensörü kayıyor
- vakum pompası odada birkaç Hz'lik basınç dalgalanması oluşturuyor
- her uçuşta motor itkisi (~%3) ve sürükleme (~%5) biraz farklı

Kendi kayıtlarınla çalıştırmak için dosyaları aynı adlarla bir klasöre koyup `--veri` ile vermen yeterli. `vakum_referans.csv`'ye vananın açıldığı anı, `ucus_referans.csv`'ye zemin basıncını yazman gerekiyor. Gerçek bir uçuşta tepe noktasının doğru zamanı bilinmediği için `gercek_tepe_s` sütunu boş bırakılabilir; o zaman rapor yöntemleri doğru/yanlış diye işaretlemiyor.

## Kullanım

```
pip install -r requirements.txt
python ucusrapor.py
```

Rapor `rapor/UKB_karsilastirma.xlsx` olarak kaydediliyor. Yöntemleri çok sayıda simüle uçuşla denemek için `python ucus_tekrar.py`. Gerçek kayıtlarla çalışırken `--gercek` eklersen rapordaki "örnek veri" uyarısı kalkıyor. Rapordaki çıkarım cümleleri sonuçlardan hesaplanıyor, yani veri değişince onlar da değişiyor. Zamanlayıcı yedeğinin süresi varsayılan olarak 20,9 s (örnek uçuş simülasyonundan); kendi roketin için `--zamanlayici` ile değiştirebilirsin. Örnek veriyi yeniden üretmek için `python veri_uret.py`, testler için `python -m pytest`.

- Özgün kart formatı: `t_ms, basinc_pa, sicaklik_c, ax_g, ay_g, az_g, durum`
- Ticari kart formatı: `zaman_s, irtifa_m, olay` (ticari kartın dışa aktarımını bu sütunlara çevirmek gerekiyor)

## Örnek veriyle çıkan sonuçlar

Bu sonuçlar büyük ölçüde örnek veriye koyduğum varsayımlardan (pompa dalgalanması, ses hızı civarındaki basınç hatası, ivmeölçer doyumu) geliyor. Aracın bu etkileri yakalayabildiğini gösteriyor; gerçek kartlarımızın tam olarak böyle davrandığını değil.

- Mevcut basit barometrik algoritma, vakum testlerinin üçünde de pompanın dalgalanması yüzünden 40-60 s erken tetikledi; örnek uçuşta da ses hızı civarında, ~1270 m'de tetikliyor.
- Sadece filtre eklemek yetmiyor. İvmeölçer doyuma girdiği için ivmeden hesaplanan hız düşük çıkıyor ve Mach kilidi de erken açılıyor.
- Kalkıştan sonraki ilk 10 s barometreyi yok sayan zaman kilidi + filtre, örnek uçuşta tepe noktasını ~0,8 s geç buluyor.
- Rampada, hakem altimetresi takıldıktan sonra iki kartın süreklilik ve telemetri bağlantısının tekrar kontrol edilmesi gerekiyor.

Tek bir örnek uçuşta bir yöntemin tutması şans olabilir. `python ucus_tekrar.py` farklı gürültü, SD kart hataları ve itki/sürükleme sapmalarıyla varsayılan olarak 100 uçuş üretip her yöntemi dener. `--n 200` ile çıkan sonuç (±1 s içinde = uygun):

| Yöntem | Uygun | Erken | Geç |
|---|---|---|---|
| Basit barometrik (mevcut) | %0 | %100 | %0 |
| Filtreli barometrik | %22 | %76 | %2 |
| İvme entegrasyonu | %2 | %95 | %2 |
| Mach kilitli + filtreli | %28 | %70 | %2 |
| Zaman kilitli + filtreli | %90 | %0 | %10 |
| Zamanlayıcı | %78 | %22 | %0 |

Zaman kilidi hiç erken tetiklemedi; geç kaldığı uçuşlarda gecikme en fazla ~1,2 s. Zamanlayıcı itki ve sürükleme değiştikçe kayıyor, bu yüzden tek başına değil yedek olarak düşünülmeli.

## Süreç

Mevcut durum:

![Mevcut süreç](docs/surec_mevcut.drawio.svg)

Önerdiğim süreç:

![Önerilen süreç](docs/surec_onerilen.drawio.svg)

Diyagramları draw.io ile hazırladım. `.drawio.svg` dosyaları GitHub'da resim olarak görünüyor, draw.io'da açılıp düzenlenebiliyor.

## Eksikler

- Gerçek test kaydıyla henüz denenmedi. Bir sonraki test döneminde iki kartın kayıtlarını toplayıp aynı raporu çıkarmayı planlıyorum.
- Ticari kartın gerçek dışa aktarım formatına göre bir okuyucu yazılmadı, şimdilik sütunları elle çevirmek gerekiyor.
- Zaman kilidi süresi uçuş simülasyonundan seçildi, farklı bir motor ya da roket için yeniden ayarlanmalı.
- Saat hizalaması irtifa eğrilerini üst üste getiriyor. Ticari kart irtifayı kendi filtresinden geçirdiği için (~0,2 s gecikme) bulunan saat farkı gerçekte olandan ~0,2 s küçük çıkıyor. İki karta ortak bir tetik sinyali kaydettirmek bunu çözer.

---

Büşra Şen · İstanbul Medipol Üniversitesi, Yönetim Bilişim Sistemleri
