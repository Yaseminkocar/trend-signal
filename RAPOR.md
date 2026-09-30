# Kargo/Teslimat Konuşmalarında Erken Trend Sinyali

Konu: Türkiye'de kargo ve teslimat şikayetleri. Kaynaklar: X (sosyal medya) ve Ekşi Sözlük (sözlük); TikTok ve Instagram denendi.
Analiz anı: `2026-09-30T00:00+03:00`. Son 7 gün 23-29 Eylül, önceki 7 gün 16-22 Eylül.
Tekrar üretmek için: `python -m trend analyze --asof 2026-09-30T00:00:00+03:00` (çıktının kopyası `reports/signals_2026-09-30.md`). Arayüzle: `streamlit run app.py`, konu `kargo`, "Kayıtlı veriyle analiz et".

## 1. Sonuç

Doğrulanmış bir yükseliş yok. Genel hacim düz: önceki hafta 135, son hafta 143 tekil içerik (temiz puan +0.10).
En güçlü aday Kolay Gelsin. Ekşi'de önceki hafta 1, son hafta 8 tekil entry var ve bunlar 7 farklı yazardan, 5 farklı günden geliyor. Ancak artış X'te görünmüyor, yani tek kaynaklı. Bu yüzden sonucu doğrulanamadı olarak işaretledim.

Bu çalışmadaki en önemli bulgu, toplama sürecinin kendisinin iki kez sahte yükseliş üretmesi ve bunu yakalayıp kurala bağlamam oldu (5. bölüm).

| Aday | Önceki | Son | Temiz puan | Durum | Neden aday, eksik olan ne |
|---|---|---|---|---|---|
| Firma: Kolay Gelsin | 1 | 8 | +2.17 | Doğrulanamadı | 7 yazar, 5 gün, en yoğun gün %38. Eksik: ikinci kaynak. X örnekleminde (236 tweet) bu firma son 7 günde hiç geçmiyor. |
| Tema: ücret/zam | 0 | 2 | +1.58 | Doğrulanamadı | Oran yüksek ama sadece 2 içerik, 2 yazar, 2 gün. Eksik: hacim. |
| Tema: gecikme | 16 | 21 | +0.37 | Yükseliş yok | En büyük şikayet teması, ama artış 1.3 kat ve eşik 2 kat. |

Kolay Gelsin kanıtları (Ekşi, tarih İstanbul saati, veri zamanı 29.09.2026):
[186621157](https://eksisozluk.com/entry/186621157) 23.09 18:15,
[186656826](https://eksisozluk.com/entry/186656826) 25.09 11:02,
[186716346](https://eksisozluk.com/entry/186716346) 27.09 21:14,
[186717045](https://eksisozluk.com/entry/186717045) 27.09 21:40,
[186718120](https://eksisozluk.com/entry/186718120) 27.09 22:22.
Entry'lerde "ciddi bozgun", kurye tavrı, "kutuları paramparça" gibi ifadeler var; tek bir olaydan çok genel bir hizmet düşüşünü anlatıyorlar. Instagram'da 24.09 tarihli tek bir tüketici şikayeti de aynı yönde ([DdrApuSoNpz](https://instagram.com/p/DdrApuSoNpz)).

Sonraki adım: Kolay Gelsin'i X'te tek terimli bir sorguyla (`"kolay gelsin" kargo`) 14 gün boyunca ayrıca toplamak. Artış X'te de görülürse aday "yükseliş adayı" olur, görülmezse Ekşi'ye özgü bir tartışma olarak kapanır.

## 2. Kaynaklar

| Kaynak | Erişim | Ulaşılan veri | Tarih | Profil ve önceki paylaşımlar | Sorunlar |
|---|---|---|---|---|---|
| X | Yan hesap cookie'si, Playwright | Tweet metni, id, etkileşim | Var (UTC) | Var: hesap yaşı, takipçi/takip/tweet sayısı, son 20 tweet (48 profilin 43'ünde) | Kütüphaneler bozuk, tarih filtresi bazı sorgularda çalışmıyor, rate limit |
| Ekşi Sözlük | Girişsiz, Scrapling | Entry metni, yazar, favori, düzenlenme | Var (dakika, TR saati) | Yazar sayfası var, kullanmadım | Tarih filtresi yok, aramada konu dışı başlıklar |
| TikTok | Girişsiz, Playwright | 9 aramada 184 video, son 14 günde sadece 9 | Var | Takipçi sayısı var | Arama popülerliğe göre sıralı, eski içerik geliyor |
| Instagram | Girişsiz login duvarı; yan hesapla 502 gönderi, son 14 günde 90 | Gönderi metni, beğeni | Var | Kullanıcı adı | Elle kontrol ettiğim 90 gönderinin 80'i satış ilanı ya da kurumsal paylaşım |

Sinyali varsayılan olarak X ve Ekşi ile hesaplıyorum. X metin tabanlı ve en zengin profil verisini veriyor; Ekşi ise tarihli ve tam sayılabilen tek kaynak. TikTok ve Instagram verisi de toplanıyor, `--sources` ile analize eklenebiliyor (neden varsayılan olmadığı 5. bölümde).

## 3. Araç seçimi

Araçları aynı Ekşi sayfası ve aynı parser ile ölçtüm (`bench/compare_tools.py`, 3 deneme):

| Araç | Sonuç | Ortalama süre | Kurulum | Not |
|---|---|---|---|---|
| requests + BeautifulSoup | 10/10 entry | 0.89 sn | 2 paket | Çalışıyor ama TLS parmak izi bot gibi görünüyor |
| Scrapling (Ekşi için seçtim) | 10/10 | 0.55 sn | Tek paket | Tarayıcı gibi görünüyor, Cloudflare gelirse tek satırla tarayıcı moduna geçiyor |
| Playwright (X için seçtim) | 10/10 | 2.22 sn | Chromium indirmesi | JavaScript isteyen X için çalışan tek yol |
| Crawl4AI | 10/10 | 1.91 sn | Yaklaşık 70 ek paket | LLM odaklı; bu iş için fazla ağır |
| twikit (X) | Çalışmadı | | | X istek imzalamayı değiştirmiş, kütüphane geride kalmış |

Ekşi'de JavaScript gerekmediği için en hafif ve en hızlı seçenek Scrapling oldu. X'te kütüphaneler kırılgan olduğu için gerçek tarayıcıda X'in kendi ağ yanıtlarını dinlemeyi seçtim; sayfa tasarımı değişse bile veri formatı daha az değişiyor.

## 4. Veri toplama ve kalite

Ortak kayıt (`data/kargo/records.jsonl`): `source, url, text, published_at (saat dilimli ya da boş), collected_at, author (maskeli), query, extra`.

- Tekrarlar: Her kaydın anahtarı kaynak ve temizlenmiş URL'den üretiliyor, aynı komut tekrar çalışınca kayıt çoğalmıyor. Metni neredeyse aynı içerikler de analizde tek sayılıyor.
- Eksik tarih: Saat bilgisi yoksa yayın zamanını boş bırakıyorum, tahmin etmiyorum.
- Gizlilik: Kullanıcı adları ve @etiketler geri çevrilemeyecek şekilde maskeleniyor; ilanlardaki telefon numaraları `[tel]` oluyor.
- Hacim: 669 kayıt (Ekşi 187, X 383, Instagram 90, TikTok 9) ve 48 X profili. Analize giren: son hafta 109 tweet ve 34 entry, önceki hafta 107 tweet ve 28 entry.

Sorun günlüğü. Otomatik kayıtlar `data/kargo/issues.jsonl` dosyasında. Karşılaştığım başlıca sorunlar ve nasıl çözdüğüm:

| Sorun | Kaynak | Nasıl ele aldım |
|---|---|---|
| Tarihe göre filtreleme yok, gün parametresi sayfa bulunamadı hatası verdi | Ekşi | "Son N sayfayı al" yöntemi önceki haftayı eksik sayacağı için kullanmadım. Başlığın son sayfasından geriye, istediğim tarihe ulaşana kadar sayfa sayfa gidiyorum. |
| Aramada "tsk kargo uçağı" gibi konu dışı başlıklar geldi | Ekşi | Konu dosyasına dışlama listesi ekledim; elenen her başlık sorun günlüğüne yazılıyor, sessizce kaybolmuyor. |
| Uzun sorgularda tarih filtresi çalışmadı: iki farklı gün aynı 20 tweeti döndürdü | X | Ham yanıtları kaydedip karşılaştırarak fark ettim. Sorguları sadeleştirdim ve her tweetin gerçekten istenen günde atılıp atılmadığını kodda ayrıca kontrol ettim (1601 tweet elendi). |
| Arama kullanıcı adlarını da eşleştiriyor, voleybol tweetleri geldi | X | Metinde konu kelimesi geçmeyen içeriği eleyen bir alaka filtresi ekledim. |
| Rate limit yüzünden günler boş döndü | X | Boş günde bekleyip bir kez daha deniyorum; sadece boş kalan günleri yeniden toplayan `--fill-gaps` seçeneği ekledim; veri her gün sonunda diske yazılıyor, yarıda kesilen toplama kaybolmuyor. |
| Bazı günlerde yüzlerce tweet var, örnek doyuyor | X | Her sorgu ve gün için üst sınır koydum. X sayılarını hacim olarak değil örnek içindeki pay olarak yorumluyorum ve bunu sınır olarak belirtiyorum. |
| Instagram'daki gönderilerin çoğu satış ilanı | Instagram | Açıklanabilir bir ilan filtresi yazdım ve 99 gönderiyi elle etiketleyip filtrenin başarısını ölçtüm (5. bölüm). |
| "bmw 3" yazınca Ekşi'deki "bmw 3 serisi" başlığı bulunmadı | Ekşi | Canlı denemede fark ettim. Her anahtar kelimeyi ayrı arıyorum; tam ifade sonuç vermezse en uzun kelimeyle arayıp bütün kelimeleri içeren başlıkları alıyorum ("bmw 3" ile "bmw 3 serisi" eşleşiyor, "bmw x5" eşleşmiyor). |
| Yeni konuda X toplaması 30-40 dakika sürdü | X | Neyin zaman aldığını ölçtüm (boş günlerde bekleme, profil sayısı). Arayüze hızlı toplama modu ekledim; çok uzun toplamalar için tarayıcıya bağlı olmayan komut satırını öneriyorum. |

Hesap profili ve bot tahmini (`trend/profiles.py`): Kurallarla puanlıyorum ve her kural bir gerekçe yazıyor: hesap yaşı (30 günden genç +2, 180 günden genç +1), günlük paylaşım sayısı (20'den fazla +1, 50'den fazla +2), son 20 paylaşımda tekrar oranı (%30 üstü +1, %50 üstü +2), takipçisi 10'dan az ve takip ettiği 200'den fazla (+1), varsayılan profil fotoğrafı (+1), 4 haneli rakamla biten kullanıcı adı (+1). 4 ve üstü "bot olası", 2-3 "şüpheli". 48 hesabın 45'i gerçek olası, 3'ü şüpheli çıktı, bot olası hesap çıkmadı. Bot olası hesaplar analizde otomatik dışlanıyor. Sınır: Bu kurallar kaba spam'i yakalar, normal görünen koordineli hesapları yakalamaz.

## 5. Sinyal yöntemi ve belirsizlik

Gruplama: Her kaydı iki açıdan grupluyorum. *Tema* için 8 temalı bir kelime kökü sözlüğü kullanıyorum; kelime başından eşleştirdiğim için "zam" kökü "zaman" kelimesini yakalamıyor. *Firma* Ekşi'de başlıktan, X'te metinden çıkıyor. Olası yanlış birleşmeler: PTT başlığında başka firmayı anan entry PTT'ye yazılıyor; içeriğin %65'i belirli bir sorun söylemediği için "diğer" temasında kalıyor.

Puan: temiz puan = log2((son + 1) / (önceki + 1)). Sayımda neredeyse aynı içerikler tek sayılıyor ve bot olası hesaplar çıkarılıyor. tekrar etkisi = ham puan - temiz puan, yani artışın ne kadarının kopyalardan geldiği. Temiz puan 1'in üstündeyse (yaklaşık 2 kat) grup aday oluyor.

Filtreleme yaklaşımım: "Yükseliş var" demeden önce veriyi üç aşamada ayıklıyorum ve her aşama neyi neden çıkardığını gösteriyor. Toplarken tarih dışı, konu dışı ve ilgisiz içerik ayrılıyor. Analizden önce ilanlar, günlük üst sınırı aşan kayıtlar, iki dönemi eşit kapsamayan sorgular, kopyalar ve bot olası hesaplar çıkıyor. Karar verirken de şu kontroller aranıyor: en az 5 tekil içerik, en az 3 yazar, en az 3 gün, hiçbir günün payı %60'ı geçmemeli, en az 2 kaynak, dönemler dengeli kapsanmış olmalı. Biri eksikse sonuç doğrulanamadı oluyor ve eksik olan yazılıyor. Arayüzde her filtre açılıp kapatılabiliyor.

Sahte yükseliş 1: toplama süreci. İlk tam analizde 3 "yüksek güvenli yükseliş" çıktı (Kolay Gelsin 2'den 13'e, gecikme 12'den 31'e). Sonuca güvenmeden önce ham veriye baktım: firma sorgusunun 22 tweetinin hepsi 29 Eylül tarihliydi, çünkü o sorgu diğer günlerde rate limit yüzünden boş dönmüştü. Artış konuşmada değil toplamadaydı. İki kural ekledim ve testle korudum: iki dönemi dengeli kapsamayan sorgu analiz dışı kalıyor, bir gün için toplanabilecek kayıt sayısı sınırlı. Aynı veri bundan sonra "yükseliş yok / doğrulanamadı" verdi.

Sahte yükseliş 2: Instagram. Instagram ve TikTok'u eklediğimde 4 grup "yüksek güvenli yükseliş" oldu. İnceleyince ücret temasındaki artışın satış ilanlarından geldiğini ("Fiyat: 200 TL, PTT kargo ile gönderiyoruz"), etiket sayfasının yeni gönderileri öne çıkardığını ve "kolay gelsin" selamlaşmasının firma sanıldığını gördüm.

- İlan filtresi (`trend/analysis/ads.py`): Her gönderiyi fiyat, sipariş/iletişim, satış koşulu, kampanya, kurumsal dil ve iş ilanı kurallarıyla puanlıyorum. Şikayet dili puanı düşürüyor, çünkü şikayet eden bir satıcı da tüketici sesidir. Puan 2 ve üstüyse gönderi çıkıyor ve gerekçesi görülüyor.
- Ölçüm: 99 gönderiyi ticari ve bireysel diye etiketledim (`data/kargo/ad_labels.csv`, `python bench/eval_ads.py`). İlan dediği 70 gönderinin 69'u gerçekten ilan (kesinlik 0.99), 80 ilanın 69'unu yakalıyor (duyarlılık 0.86), 19 bireysel gönderinin 18'ini koruyor. Kurallar bu veriye bakılarak yazıldığı için yeni veride sonuç daha düşük olabilir.
- Etkisi: 4 sahte aday 0'a indi (`reports/signals_2026-09-30_tum_kaynaklar.md`). Filtreden sonra Instagram'da 20, TikTok'ta 9 gönderi kalıyor; bu kaynaklar artık sonucu bozmuyor ama katkı vermek için de az. Bu yüzden varsayılan sinyal X ve Ekşi.
- Pay kontrolü: X, Instagram ve TikTok örnek verdiği için bu kaynaklarda sayıya değil grubun o dönemdeki payına da bakıyorum. Toplam sayı yeni gönderilere kaydığı için artsa bile payı artmayan grup aday olamıyor.

Testler: 62 test, internet gerektirmiyor (`python -m pytest`). Tekrar kayıt, eksik tarih, dönem sınırları, 30 kopya spam'in sahte artış yaratmaması, bot hesabın dışlanması, tek kaynak ve tek günün "doğrulanamadı" vermesi, kaydedilmiş sayfalarla parser'lar, ilan filtresi ve başlık eşleştirme test ediliyor.

Sonraki adımlar: Instagram ve TikTok'u her gün aynı saatte toplamak; TikTok'ta açıklama yerine yorumları toplamak; video sesini Whisper, üzerindeki yazıyı OCR ile metne çevirmek; ilan filtresini etiketli veriyle ölçülen küçük bir LLM sınıflandırıcıyla karşılaştırmak.

## 6. Yeniden kullanım: başka konu, başka dönem

Case "yeniden çalıştırılabilir" bir prototip istiyor. Bunu yalnız "aynı komut aynı sonucu verir" olarak değil, "bir marka başka bir konu ya da dönem için de kullanabilir" olarak ele aldım:

- Konu koddan ayrı. Konuya özgü her şey `topics/<konu>.json` dosyasında: başlıklar, sorgular, alaka kelimeleri, temalar, markalar. Toplama, temizleme, bot tahmini ve kıyas konudan bağımsız.
- Tek adım. `python -m trend run "elektrikli scooter"` ya da arayüzdeki arama kutusu, konu dosyası yoksa anahtar kelime ve markalardan oluşturuyor, veriyi topluyor ve analiz ediyor.
- Dönem seçilebiliyor. Kıyas 7, 14 ya da 21 gün olabiliyor; `--asof` ve `--until` ile geçmiş bir dönem de incelenebiliyor.
- Arayüz. Komut satırı bilmeyen biri için isteğe bağlı bir Streamlit arayüzü ekledim: konu yazılıyor, kaynaklar ve dönem seçiliyor, filtreler açılıp kapatılıyor; sonuçlar, eksik kanıt ve kanıt linkleri aynı ekranda. Komut satırıyla aynı analiz fonksiyonunu kullandığı için aynı veride aynı sonucu veriyor.

Canlı denemeler (30 Eylül). Sistemi gündemdeki konularla arayüzden denedim:

- *BMW 3 serisi:* Ekşi'de önceki hafta 1, son hafta 277 entry, ama 271'i tek günde (yeni modelin tanıtımı). Sonuç doğrulanamadı, eksik "tek güne yığılma %98".
- *Akaryakıt zammı:* fiyat/zam teması 9'dan 58'e çıktı, 58 yazar, Ekşi ve X. Eksik yine tek gün: içeriğin %72'si zam günü olan 25 Eylül'de.
- *iPhone 18 Pro, 21 günlük kıyas:* X'te yükseliş adayı çıktı (önceki [ÖNCEKİ], son [SON], temiz puan [PUAN]).

İlk iki konu gerçek olaylardı ve sistem onları yakaladı, ama tek günlük bir tepkiyi trend saymadı; iPhone'da ise konuşma günlere yayıldığı için aday çıktı. Bu denemeler iki eksik de gösterdi ve ikisini düzelttim: "bmw 3" başlığı bulamıyordu (4. bölüm), X'te tek sorgu kalınca pay kontrolü anlamsız biçimde "eksik" diyordu.

Sınırlar: İyi bir tema sözlüğü alan bilgisi istiyor, otomatik üretilen konu dosyası bir başlangıç. Instagram ilanları, "kolay gelsin" gibi günlük ifadeler ve X'in tarih filtresi her yeni konuda yeniden kontrol edilmeli.

## 7. İleriye bakış: LangGraph ve RAG

LangGraph, toplama ve karar akışını adım adım bir graf olarak kurmak için uygun: topla, kapsamayı kontrol et, eksik günleri yeniden topla, grupla, puanla, aday varsa ikinci kaynakta hedefli sorgu at, raporla. Bugün elle yaptığım "Kolay Gelsin'i X'te ayrıca ara" adımı koşullu bir dal olarak otomatikleşir.

RAG iki yerde işe yarar. Gruplamada, kelime sözlüğü yerine benzer şikayetleri geçmiş etiketli örneklerle eşleştirip "diğer" temasındaki %65'i anlamlı gruplara ayırabilir. Raporda, aday bir sinyal için geçmiş haftaların benzer konuşmalarını getirip "bu yeni mi, mevsimsel mi" sorusuna kanıtla cevap verebilir. İki durumda da son karar bugünkü açıklanabilir eşiklerle verilmeli ve kanıt URL'si olmayan bir LLM çıktısı kabul edilmemeli.

## 8. AI ile çalışma

Araç: Claude (Cowork). Kod yazma, hata ayıklama ve test yazma sırasında birlikte çalıştığım bir araç olarak kullandım. Projenin yönünü ve kararları ben belirledim: konu, kaynaklar, yan hesaplarla veri toplama, konuyu koddan ayırıp yeniden kullanılabilir yapma, arayüz. Her adımı kendi bilgisayarımda çalıştırıp çıktısını kontrol ettim.

Nasıl çalıştım: İşi küçük parçalara böldüm (önce iskelet ve testler, sonra Ekşi, araç ölçümü, X, analiz, arayüz). Her parçada önce testleri çalıştırdım, sonra canlı siteyi tek başlık ya da tek gün gibi küçük denemelerle yokladım. Bir hata olduğunda tahminle düzeltmek yerine ham yanıtı kaydedip veriye baktım.

Doğrulama: Her değişiklikten sonra testleri çalıştırdım, günlere dağılımı kontrol ettim ve her bulguyu URL'sine kadar izledim. En önemli kural "iyi görünen sonuca güvenme" oldu: iki kez "yüksek güvenli yükseliş" çıktı, ikisinde de ham veriyi açtım ve ikisinin de toplama sürecinden kaynaklandığını gördüm.

AI'ın yanıldığı yerler (tam liste `AI_NOTLARI.md`): X'in tarih filtresini UTC sandı; "kolay gelsin" selamlaşmasını firma adı sandı; ilan filtresinde Türkçe harf dönüşümünde ö ile ç'yi karıştırdı; arayüzde konu değişince eski toplamayı durduramayan bir hata yaptı, bu yüzden kargo verisine istemeden yeni kayıt eklendi. Bunların hepsini çıktıları kontrol ederken ya da canlı denemede fark ettim ve düzelttirip test ekledim.

Ders: AI hızlı ilerlememi sağladı, ama canlı sistemler hakkındaki varsayımları ve iyi görünen sonuçları küçük denemelerle ve ham veriyle doğrulamak benim işimdi.

Etik not: X ve Instagram kullanım koşulları otomatik veri toplamayı kısıtlıyor. Az veri, yan hesap ve maskeli teslimle yalnızca bu prototip için çalıştım. Gerçek kullanımda resmi API ya da lisanslı veri sağlayıcı gerekir.
