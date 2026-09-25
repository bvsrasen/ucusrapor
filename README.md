# UçuşRapor

Roket takımımızda (ÇGM AKANA, TEKNOFEST Orta İrtifa) her test ya da uçuştan sonra aviyonik kartın SD karta yazdığı veriyi Excel'e aktarıp elle temizliyor, grafikleri tek tek çiziyorduk. Tek bir raporu hazırlamak neredeyse 3 saat sürüyordu ve her seferinde farklı bir formatta çıkıyordu.

Bu projede o süreci otomatikleştirmeye çalıştım: log dosyasını tek komutla okuyup temizleyen, temel uçuş metriklerini hesaplayan ve standart bir Excel raporu çıkaran küçük bir Python aracı.

![Rapor özeti](docs/rapor_ozet.png)

## Ne yapıyor?

- Tekrar eden satırları, boş hücreleri ve bozuk durum kodlarını buluyor
- Sensör sıçramalarını (ör. bir anda 9999 m irtifa) yakalayıp komşu değerlerden düzeltiyor
- Maksimum irtifa, apogee zamanı, maksimum ivme, paraşüt açılma anları ve iniş hızlarını hesaplıyor
- Sonuçları grafikli bir Excel raporuna yazıyor; düzeltilen her satır "Veri Kalitesi" sayfasında listeleniyor

Metrikleri hem Python'da hem de Excel formülleriyle hesaplatıyorum, ikisi tutmazsa rapordaki "Kontrol" sütunu bunu gösteriyor.

## Kullanım

```
pip install -r requirements.txt
python ucusrapor.py veri/ucus_log_simule.csv
```

Rapor `rapor/` klasörüne kaydediliyor. Gerçek bir uçuş logu için komutun sonuna `--gercek` eklenebilir.

Testleri çalıştırmak için: `python -m pytest`

## Veri hakkında

Takımın gerçek uçuş verisini paylaşamadığım için `veri_uret.py` ile bizim uçuş profilimize benzeyen simüle bir kayıt ürettim. İçine bilerek 26 hata ekledim (listesi `veri/beklenen_hatalar.json` içinde), testler bunların hepsinin yakalanıp yakalanmadığını kontrol ediyor.

Log formatı: `zaman_ms, irtifa_m, basinc_hPa, ivme_x_g, ivme_y_g, ivme_z_g, sicaklik_C, durum`

`durum` sütunu, STM32'deki uçuş durum makinesinin aşaması (0: rampa, 1: kalkış, 2: motor yanması, 3: süzülme, 4: apogee, 5: sürüklenme paraşütü, 6: ana paraşüt, 7: iniş).

## Süreç

Kodlamaya başlamadan önce mevcut süreci ve hedef süreci BPMN ile çizdim (`docs/` klasöründe, draw.io dosyaları da orada). Projeyi iki sprint halinde Jira'da takip ettim; gereksinimleri, test senaryolarını ve kullanım kılavuzunu Confluence'ta yazdım.

Mevcut süreç:

![as-is](docs/bpmn_as_is.png)

Hedeflenen süreç:

![to-be](docs/bpmn_to_be.png)

## Eksikler / sonraki adımlar

- Henüz gerçek bir uçuş logunda denenmedi
- Sıçrama eşikleri bizim roketin profiline göre ayarlı, başka bir roket için gözden geçirilmesi gerekir
- Birden fazla uçuşu karşılaştıran bir rapor eklemek istiyorum

---

Büşra Şen · İstanbul Medipol Üniversitesi, Yönetim Bilişim Sistemleri
