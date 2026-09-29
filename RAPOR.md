# RAPOR: Kargo/teslimat konuşmalarında erken trend sinyali

**Konu:** Türkiye'de kargo/teslimat şikâyetleri. **Kaynaklar:** X (sosyal medya) + Ekşi Sözlük (sözlük).
**Analiz anı (asof):** `2026-09-30T00:00+03:00`. Son 7 gün: 23–29 Eylül; önceki 7 gün: 16–22 Eylül.
**Tekrar üretmek için:** `python -m trend analyze --asof 2026-09-30T00:00:00+03:00` (çıktının kopyası: `reports/signals_2026-09-30.md`).

## 1. Sonuç

**Doğrulanmış bir yükseliş yok.** Genel hacim düz: 135 → 143 tekil içerik (temiz puan +0.10).
En güçlü aday **firma: Kolay Gelsin**. Ekşi'de 1 → 8 tekil entry var; bu entry'ler 7 farklı yazardan ve 5 farklı günden geliyor. Ancak artış X'te görülmüyor, yani tek kaynaklı. Bu yüzden sonuç **DOĞRULANAMADI** (güven: düşük).

Raporun en önemli bulgusu, sürecin kendisinin ürettiği **sahte bir yükseliş** oldu. Nasıl yakalandığı §5'te anlatılıyor.

| # | Aday | Önceki → Son (tekil) | Temiz puan | Durum | Neden aday / eksik olan |
|---|---|---|---|---|---|
| 1 | firma:kolay_gelsin | 1 → 8 | +2.17 | DOĞRULANAMADI | 7 yazar, 5 gün, tek güne yığılma %38. **Eksik:** ikinci kaynak. X örnekleminde (236 tweet) bu firma son 7 günde hiç geçmiyor; TikTok'ta son 14 günde hiç video yok. |
| 2 | tema:ucret_zam | 0 → 2 | +1.58 | DOĞRULANAMADI | Oransal artış var ama yalnızca 2 içerik, 2 yazar, 2 gün. **Eksik:** hacim. |
| 3 | tema:gecikme | 16 → 21 | +0.37 | yükseliş yok | En büyük şikâyet teması ama ~1.3 kat artış eşiğin (2 kat) altında. |

Kolay Gelsin için kanıtlar. Hepsi Ekşi entry'si; tarih Europe/Istanbul, veri zamanı 29.09.2026:
[186621157](https://eksisozluk.com/entry/186621157) 23.09 18:15 ·
[186656826](https://eksisozluk.com/entry/186656826) 25.09 11:02 ·
[186716346](https://eksisozluk.com/entry/186716346) 27.09 21:14 ·
[186717045](https://eksisozluk.com/entry/186717045) 27.09 21:40 ·
[186718120](https://eksisozluk.com/entry/186718120) 27.09 22:22.
Entry içerikleri "ciddi bozgun", kurye tavrı, "kutuları paramparça" gibi. Bunlar tek bir olaya değil, genel bir hizmet düşüşüne işaret ediyor.
Destekleyici ama tek bir gönderi olan kanıt: Instagram'da 24.09 tarihli bir tüketici şikâyeti ("Kolay gelsin kargo firması tam 12 gündür kargomu teslim edemedi", [DdrApuSoNpz](https://instagram.com/p/DdrApuSoNpz), veri zamanı 29.09.2026). Instagram'ın neden sinyal hesabına alınmadığı §5'te.

**Uygulanabilir sonraki adım:** Kolay Gelsin'i X'te firma adıyla, *tek terimli* bir sorguyla (`"kolay gelsin" kargo`) 14 gün boyunca ayrı ayrı toplamak. Artış X'te de görülürse aday "yükseliş adayı"na çıkar. Görülmezse Ekşi'ye özgü bir tartışma olarak kapanır.

## 2. Kaynaklar

| Kaynak | Erişim | Ulaşılan veri | Tarih | Profil/önceki paylaşım | Sorunlar |
|---|---|---|---|---|---|
| **X** | Yan hesap cookie'si + Playwright (gerçek Chromium) | Tweet metni, id, dil, etkileşim sayıları | Var (saniye, UTC) | **Var:** hesap açılış tarihi, takipçi/takip/tweet sayısı, 20 önceki tweet (48 profilin 43'ünde) | twikit bozuk; tarih filtresi bazı sorgularda yok sayılıyor; rate limit; günlük örnekleme (§3) |
| **Ekşi Sözlük** | Login yok, Scrapling | Entry metni, yazar, favori sayısı, düzenlenme bilgisi | Var (dakika, TR saati) | Yazar sayfası var, kullanılmadı: sözlükte bot tahmini case'in odağı değil | `?day=` filtresi 404 verdi; aramada konu dışı başlıklar çıktı |
| TikTok | Login yok, Playwright (`collect tiktok`) | 9 aramada 184 video; **son 14 günde yalnız 9** (172'si eski) | Var (`createTime`) | Takipçi sayısı var, hesap yaşı yok | Arama tarihe göre değil popülerliğe göre sıralı; tarih filtresi yok |
| Instagram | Girişsiz: 1. sayfadan sonra **login duvarı**. Yan hesap `sessionid` ile: 6 etikette 502 gönderi, son 14 günde **90** | Gönderi metni, beğeni/yorum | Var (`taken_at`) | Kullanıcı adı var, profil çekilmedi | Gönderilerin **%54'ü satış ilanı** (fiyat, WhatsApp, "sipariş için DM"); etiket sayfası yeniye kayık |

Girişsiz ilk deneme `bench/social_probe.md` dosyasında (oradaki "captcha" sütunu güvenilmez; sayfa kaynağında kelime araması). TikTok ve Instagram verisi `data/kargo/records.jsonl` içinde duruyor ama **sinyal hesabı X + Ekşi ile yapılıyor** (`config.SIGNAL_SOURCES`; `--sources` ile değiştirilebilir). Gerekçeler: X metin tabanlı ve en zengin profil verisini veriyor. Ekşi ise tarihli ve **tam sayılabilen** tek kaynak (§3).

## 3. Araç seçimi

Aynı Ekşi sayfası ve aynı parser ile ölçüldü (`bench/compare_tools.py`, 3 deneme, macOS, Python 3.12):

| Araç | HTTP | Entry/tarihli | Ort. süre | Kurulum/bakım | Not |
|---|---|---|---|---|---|
| requests + BS4 | 200 | 10/10 | 0.89 s | 2 paket | Şu an engellenmiyor ama TLS parmak izi "bot" gibi görünüyor |
| **Scrapling** (seçildi, Ekşi) | 200 | 10/10 | **0.55 s** | Tek paket, curl_cffi | Tarayıcı TLS parmak izi + gerçekçi başlıklar; Cloudflare gelirse `StealthyFetcher`'a geçiş tek satır |
| **Playwright** (seçildi, X) | 200 | 10/10 | 2.22 s | Chromium indirmesi (~180 MB) | JS gerektiren X için tek çalışan yol |
| Crawl4AI | 302→200 | 10/10 | 1.91 s | **~70 ek paket** (openai, scipy, nltk…) | LLM odaklı markdown çıkarımı; bu iş için gereğinden ağır |
| twikit (X) | – | – | – | – | `Couldn't get KEY_BYTE indices`: X istek imzalamayı değiştirmiş, kütüphane geride kalmış. Yedek olarak kodda duruyor |

**Karar:** Ekşi'de JavaScript gerekmediği için hafif ve en hızlı araç Scrapling. X'te ise kütüphaneler kırılgan. En sağlam yol, gerçek tarayıcıda X'in kendi GraphQL yanıtlarını dinlemek. Parser iki arka uç için de ortak ve offline test ediliyor.

## 4. Veri toplama ve kalite

**Ortak kayıt** (`data/kargo/records.jsonl`) şu alanlardan oluşuyor: `source, url, text, published_at (TZ'li ya da null), collected_at (UTC), author (maskeli), query, extra`.
- **Tekrar temizliği:** `id = sha1(kaynak | kanonik URL)`. Takip parametreleri, `www` ve sondaki `/` temizleniyor. Aynı komut tekrar çalışınca kayıt eklenmiyor (upsert). İlk `collected_at` korunuyor, sadece boş alanlar dolduruluyor. Metni aynı ya da neredeyse aynı içerikler de analizde tek sayılıyor (3-kelime shingle Jaccard ≥ 0.8).
- **Eksik tarih:** Ekşi'de saat bilgisi yoksa `published_at=null`, gün bilgisi ise `extra.published_date` alanında tutuluyor. Tahmin yapılmıyor. Toplanan 669 kaydın hepsinde tarih vardı.
- **Maskeleme:** Kullanıcı adları ve metin içindeki @mention'lar tuzlu SHA-256 ile maskeleniyor (`u_xxxxxxxxxx`); satış ilanlarındaki telefon numaraları `[tel]` ile değiştiriliyor. X URL'leri kullanıcı adı içermeyen `x.com/i/status/<id>` biçiminde.
- **Hacim:** Ekşi 187 entry. Son 14 günde 62; 9 firma başlığı + aramayla bulunan 13 aktif başlık üzerinden. X'te 383 tweet ve 48 profil var. Analize giren kısım: son 7 günde 109 tweet + 34 entry, önceki 7 günde 107 tweet + 28 entry.

**Sorun günlüğü.** Otomatik kısmı `data/kargo/issues.jsonl` dosyasında:

| Sorun | Kaynak | Ele alış |
|---|---|---|
| `?day=` filtresi 404 döndü, 0 kayıt geldi | Ekşi | Son sayfadan geriye, tarih kesimine kadar sayfalama. "Son N sayfa" yöntemi önceki haftayı eksik sayacağı için kullanılmadı |
| Aramada "11 kasım 2025 tsk kargo uçağı" gibi konu dışı başlıklar | Ekşi | Slug regex'iyle eleme (`EKSI_EXCLUDE_SLUG`), günlüğe yazılıyor |
| twikit `KEY_BYTE` hatası | X | Playwright + GraphQL dinleme |
| JavaScript ile yüklenen içerik / sonsuz kaydırma | X | Tarayıcıda kaydırma; yanıtlar ağ katmanında yakalanıyor, DOM parse edilmiyor |
| `since/until` uzun OR sorgularında yok sayıldı (28.09 ve 29.09 sorguları aynı 20 tweeti döndürdü) | X | Sorgular sadeleştirildi; `in_day` kontrolüyle gün dışı tweetler sayılmıyor (1601 tweet elendi) |
| `since/until` İstanbul saatinde çalışıyor, UTC'de değil | X | Gün kontrolü `Europe/Istanbul` |
| Arama, kelimeyi kullanıcı adı veya link kartında da eşleştiriyor (voleybol tweetleri) | X | Metinde kargo bağlamı yoksa eleme (`is_relevant`) |
| 2026 şemasında sayaçlar `legacy`'den `relationship_counts` alanına taşınmış | X | Debug dökümüyle bulundu; iki şema da destekleniyor |
| Rate limit: art arda boş sonuç (58 boş gün) | X | 60–90 s bekleyip bir kez tekrar deneme; `--fill-gaps` ile yalnız boş günleri yeniden toplama; veri her gün sonunda diske yazılıyor |
| Günlük örnekleme doyuyor ("kargom" günde yüzlerce tweet) | X | (sorgu, gün) başına en fazla 25 tweet. X sayıları **hacim değil**, günlük örnekteki pay. Sınır olarak raporlanıyor |

**Hesap profili ve gerçek/sahte tahmini** (`trend/profiles.py`): Kural tabanlı, her kural bir gerekçe cümlesi üretiyor. Hesap yaşı (<30 gün +2, <180 gün +1), ömür boyu günlük paylaşım (>20 +1, >50 +2), son 20 paylaşımda tekrar oranı (>%30 +1, >%50 +2), takipçi < 10 ve takip > 200 (+1), varsayılan fotoğraf (+1), ≥ 4 haneli rakamla biten kullanıcı adı (+1). Toplam ≥ 4 "bot olası", 2–3 "şüpheli".

**Sonuç:** 48 hesabın 45'i "gerçek olası", 3'ü "şüpheli" (ör. "hesap 25 günlük"; "varsayılan fotoğraf + rakamla biten ad"), hiçbiri "bot olası". Bot olası hesaplar analizde otomatik dışlanıyor. Bu çalıştırmada dışlanan hesap olmadı. **Sınır:** 20 tweetlik geçmiş ve basit eşikler, olsa olsa kaba spam'i yakalar; koordineli ama "normal görünen" hesapları yakalamaz.

## 5. Sinyal yöntemi ve belirsizlik

**Gruplama:** Her kayıt iki boyutta gruplanıyor.
- **tema:** 8 temalı kök-kelime sözlüğü. En çok eşleşen tema seçiliyor; kelime başı eşleşmesi kullanılıyor, böylece "zam" kökü "zaman"ı yakalamıyor.
- **firma:** Ekşi'de başlık slug'ından, X'te metinden çıkarılıyor.

Olası yanlış birleşmeler: firma başlığında başka firmayı anan entry başlık firmasına yazılıyor (PTT başlığında "cargox daha kötü"); "kurye" kelimesi gecikme şikâyetini kurye temasına çekebiliyor; "kolay gelsin" selamlaşması firma sanılıyordu (düzeltildi, §5 ikinci vaka). İçeriğin %65'i "diğer" temasında kalıyor: belirli bir sorun söylemeyen genel yorumlar.

**Puan:**
- `temiz = log2((tekil_son+1)/(tekil_önceki+1))`. Tekil sayımda yakın-tekrar kümesi 1 sayılıyor ve bot olası hesaplar hariç tutuluyor.
- `tekrar_etkisi = ham − temiz`, yani artışın ne kadarının kopyalardan geldiğini gösteriyor.
- Temiz puan ≥ 1 (yaklaşık 2 kat) ise aday.

**Aday olmanın koşulları:** ≥ 5 tekil içerik, ≥ 3 yazar, ≥ 3 gün, tek güne yığılma ≤ %60, ≥ 2 kaynak, örneklenen kaynakta dönemler arası gün kapsaması dengeli. Biri bile sağlanmazsa sonuç **DOĞRULANAMADI** olur ve eksik olan yazılır.

**Sahte yükselişi yakalama (gerçek vaka):** İlk tam analizde 3 "YÜKSELİŞ ADAYI (yüksek güven)" çıktı: Kolay Gelsin 2→13, gecikme 12→31, PTT 7→17. Ham veriye bakınca iki şey görüldü:
- Firma sorgusunun 22 "kolay gelsin" tweetinin **hepsi 29 Eylül tarihliydi.** O sorgu diğer günlerde rate limit yüzünden boş dönmüştü.
- "gelmedi/gecikti" sorgusu da yalnızca son günleri kapsıyordu.

Yani artış konuşmada değil, **toplama sürecinde** oluşmuştu. İki kural eklendi ve ikisi de testlerle korunuyor:
- **Sorgu kapsama dengesi:** Bir sorgunun verisi dönemler arasında az/çok < 0.6 oranındaysa o sorgu analiz dışı bırakılıyor.
- **(sorgu, gün) üst sınırı:** Tekrarlanan çalıştırmalar bir günü yapay olarak şişiremiyor.

Kurallardan sonra aynı veri "yükseliş yok / doğrulanamadı" sonucunu verdi.

**İkinci vaka: Instagram.** Instagram ve TikTok eklenince (`--sources eksi,x,instagram,tiktok`, çıktı `reports/signals_2026-09-30_tum_kaynaklar.md`) 4 grup "YÜKSELİŞ ADAYI (yüksek)" oldu: ücret teması 5→14, Kolay Gelsin 1→10, hasar 3→8. İnceleyince:
- Ücret teması artışı satış ilanlarından geliyor ("Fiyat: 200₺, Ptt ve Hepsijet kargo ile çalışmaktayız").
- Instagram etiket sayfası yeni gönderileri öne çıkarıyor: 90 gönderinin 25'i 29 Eylül tarihli.
- "kolay gelsin" Türkçede bir selamlaşma. "Kolay gelsin herkese, sipariş için DM" gönderisi firmaya yazılıyordu. Firma eşleşmesi "kolay gelsin kargo/firma/şube" ile sınırlandı ve test eklendi.

Bu yüzden Instagram ve TikTok toplanıyor ama sinyale alınmıyor. Tüketici şikâyeti ile satıcı ilanını ayıran bir sınıflandırıcı olmadan ölçüm yanıltıcı. Bir yan etki de oldu: "gelmedi/gecikti" sorgusu önceki haftada rate limit yüzünden yalnız 4 gün kapsadığı için (4/7) analiz dışı kaldı. Bu da X'in tema sinyallerini zayıflatıyor.

**Testler:** 47 test, internet gerekmiyor (`python -m pytest`). Kapsam: tekrar kayıt ve URL varyantları; eksik ve TZ'siz tarih; dönem sınırları; **30 kopya spam'in sahte artış yaratmaması** (ham +2, temiz < 1); bot hesabın dışlanması; tek kaynak, az kayıt, tek gün ve dengesiz kapsamanın "doğrulanamadı" vermesi; kaydedilmiş HTML/GraphQL/TikTok/Instagram yanıtlarıyla parser'lar; maskeleme; ikinci konuyla (elektrikli araç) çalışma, `--topic` ve `--until`.

## 6. Yeniden kullanım: başka konu, başka tarih

Case "yeniden çalıştırılabilir" bir prototip istiyor. Bunu yalnız "aynı komut aynı sonucu verir" olarak değil, "bir marka başka bir konu ya da dönem için de kullanabilir" olarak ele aldım:
- **Konu kod dışında.** Konuya özgü her şey `topics/<konu>.json` dosyasında: Ekşi başlıkları, sorgular, alaka kelimeleri, tema sözlüğü, markalar. Toplama, tekrar temizliği, bot tahmini, kapsama kontrolü ve 7/7 kıyas konudan bağımsız.
- **Tek komut.** `python -m trend run "elektrikli scooter"` konu dosyası yoksa anahtar kelime ve markalardan üretiyor (genel tüketici temalarıyla), veriyi topluyor ve analiz ediyor. Kullanıcı sonra sorguları ve temaları gözden geçirip tekrar çalıştırıyor. Örnek: `topics/elektrikli_arac.json`.
- **Veriler karışmıyor.** Her konu `data/<konu>/` ve `output/<konu>/` altında tutuluyor. Analiz tek komutla tekrar üretiliyor: `--asof` kıyas anını, toplamada `--until` pencerenin son gününü belirliyor.
- **Deneme.** `elektrikli_arac` konusu aynı kodla uçtan uca çalıştı. İlk çalıştırmada "elektrikli" araması elektrikli bisiklet, diş fırçası ve süpürge başlıklarını da getirdi (171 entry). Konu dosyasında arama kelimesi "elektrikli araç" yapılıp bu başlıklar dışlanınca 6 sabit + 2 bulunan başlıktan 72 entry kaldı; sonuç "yükseliş yok" (15 → 13). Yeni konuda beklenen ayar işi tam olarak bu. Bir ödünleşim de var: daha dar arama, "elektrikli araçların alınırlığı" gibi ilgili ama farklı adlı başlıkları da kaçırdı; bunlar konu dosyasına elle eklenebilir.
- **Sınırlar.** İyi bir tema sözlüğü alan bilgisi istiyor. Otomatik üretilen dosya bir başlangıç, bitmiş bir ayar değil. Ayrıca bu projede öğrenilen kaynak tuzakları her konuda yeniden kontrol edilmeli: Instagram'daki satış ilanları, "kolay gelsin" gibi günlük dildeki ifadeler, X'in tarih filtresi.

## 7. İleriye bakış: LangGraph ve RAG

**LangGraph** toplama ve karar akışını bir durum makinesi olarak modellemek için uygun: `topla → kapsama kontrolü → (dengesizse) eksik günleri yeniden topla → grupla → puanla → (aday varsa) ikinci kaynakta hedefli doğrulama sorgusu → rapor`. Bugün elle yaptığımız "Kolay Gelsin'i X'te ayrıca ara" adımı, koşullu bir kenar olarak otomatikleşir. Rate limit beklemeleri ve yeniden denemeler de graf durumunda izlenebilir.

**RAG** iki yerde işe yarar:
- **Gruplama:** Kök-kelime sözlüğü yerine embedding ile benzer şikâyetleri geçmiş etiketli örneklere eşlemek. Bugün %65'i "diğer"de kalan içeriği anlamlı temalara ayırabilir.
- **Rapor:** Aday sinyal için geçmiş haftaların benzer konuşmalarını ve kanıt URL'lerini getirip "bu yeni mi, mevsimsel mi?" sorusunu kanıta dayalı yanıtlamak.

İki kullanımda da nihai karar bugünkü açıklanabilir eşiklerle verilmeli; LLM çıktısı kanıt URL'si olmadan kabul edilmemeli.

## 8. AI ile çalışma

**Araç:** Claude (Cowork). Case analizi, mimari, kodun büyük kısmı ve testler için kullanıldı. Kodu kendi PyCharm'ımda çalıştırdım, her adımın çıktısını geri verdim, Claude da gerektiğinde ham debug dosyalarını okuyup düzeltti.

**İşe yarayan yöntemler:** İşi küçük adımlara bölmek (iskelet+testler → Ekşi → araç ölçümü → X → analiz → rapor); analiz çekirdeğini canlı veri gelmeden önce yapay veriyle test etmek; canlı siteyi tek başlık/tek gün gibi küçük denemelerle yoklamak; hata olunca tahmin yürütmek yerine ham yanıtı kaydedip (`--save-html`) veriye bakmak.

**Doğrulama:** Her değişiklikten sonra `pytest`; `python -m trend stats` ile gün dağılımı; her bulguyu URL'ye kadar izlemek; "iyi görünen" sonuçta (yüksek güvenli adaylar) veriyi açıp kaynağını kontrol etmek.

**AI'ın yanıldığı örnekler** (tam liste `AI_NOTLARI.md`'de, 9 madde): Ekşi `?day=` parametresinin çalışacağını varsaydı (404 döndü); X tarih filtresini UTC sandı; Playwright dinleyicisine hata fırlatan bir satır yazdı; "kolay gelsin" selamlaşmasını firma sandı. En önemlisi: iki kez "yüksek güvenli" yükseliş raporladı, ikisi de toplama sürecinin (X rate limit, Instagram ilanları) ürünüydü.

Ders: AI kodu hızla yazıyor, ama canlı sistem hakkındaki varsayımları ve "iyi görünen" sonuçları küçük deneme ve ham veriyle doğrulamak gerekiyor.

**Etik not:** X ve Instagram kullanım koşulları otomatik veri toplamayı kısıtlıyor. Az veri, yan hesap ve maskeli teslim ile, yalnızca bu prototip için çalışıldı. Üretimde resmi API ya da lisanslı veri sağlayıcı kullanılmalı.
