# RAPOR: Kargo/teslimat konuşmalarında erken trend sinyali

**Konu:** Türkiye'de kargo/teslimat şikâyetleri. **Kaynaklar:** X (sosyal medya) + Ekşi Sözlük (sözlük).
**Analiz anı (asof):** `2026-09-30T00:00+03:00`. Son 7 gün: 23–29 Eylül; önceki 7 gün: 16–22 Eylül.
**Tekrar üretmek için:** `python -m trend analyze --asof 2026-09-30T00:00:00+03:00` (çıktının kopyası: `reports/signals_2026-09-30.md`).

## 1. Sonuç

**Doğrulanmış bir yükseliş yok.** Genel hacim düz: 135 → 143 tekil içerik (temiz puan +0.10).
En güçlü aday **firma: Kolay Gelsin**. Ekşi'de 2 → 8 tekil entry var; bu entry'ler 7 farklı yazardan ve 5 farklı günden geliyor. Ancak artış X'te görülmüyor, yani tek kaynaklı. Bu yüzden sonuç **DOĞRULANAMADI** (güven: düşük).

Raporun en önemli bulgusu, sürecin kendisinin ürettiği **sahte bir yükseliş** oldu. Nasıl yakalandığı §5'te anlatılıyor.

| # | Aday | Önceki → Son (tekil) | Temiz puan | Durum | Neden aday / eksik olan |
|---|---|---|---|---|---|
| 1 | firma:kolay_gelsin | 2 → 8 | +1.58 | DOĞRULANAMADI | 7 yazar, 5 gün, tek güne yığılma %38. **Eksik:** ikinci kaynak. X örnekleminde (236 tweet) bu firma son 7 günde hiç geçmiyor. |
| 2 | tema:ucret_zam | 0 → 2 | +1.58 | DOĞRULANAMADI | Oransal artış var ama yalnızca 2 içerik, 2 yazar, 2 gün. **Eksik:** hacim. |
| 3 | tema:gecikme | 16 → 21 | +0.37 | yükseliş yok | En büyük şikâyet teması ama ~1.3 kat artış eşiğin (2 kat) altında. |

Kolay Gelsin için kanıtlar. Hepsi Ekşi entry'si; tarih Europe/Istanbul, veri zamanı 29.09.2026:
[186621157](https://eksisozluk.com/entry/186621157) 23.09 18:15 ·
[186656826](https://eksisozluk.com/entry/186656826) 25.09 11:02 ·
[186716346](https://eksisozluk.com/entry/186716346) 27.09 21:14 ·
[186717045](https://eksisozluk.com/entry/186717045) 27.09 21:40 ·
[186718120](https://eksisozluk.com/entry/186718120) 27.09 22:22.
Entry içerikleri "ciddi bozgun", kurye tavrı, "kutuları paramparça" gibi. Bunlar tek bir olaya değil, genel bir hizmet düşüşüne işaret ediyor.

**Uygulanabilir sonraki adım:** Kolay Gelsin'i X'te firma adıyla, *tek terimli* bir sorguyla (`"kolay gelsin" kargo`) 14 gün boyunca ayrı ayrı toplamak. Artış X'te de görülürse aday "yükseliş adayı"na çıkar. Görülmezse Ekşi'ye özgü bir tartışma olarak kapanır.

## 2. Kaynaklar

| Kaynak | Erişim | Ulaşılan veri | Tarih | Profil/önceki paylaşım | Sorunlar |
|---|---|---|---|---|---|
| **X** | Yan hesap cookie'si + Playwright (gerçek Chromium) | Tweet metni, id, dil, etkileşim sayıları | Var (saniye, UTC) | **Var:** hesap açılış tarihi, takipçi/takip/tweet sayısı, 20 önceki tweet (48 profilin 43'ünde) | twikit bozuk; tarih filtresi bazı sorgularda yok sayılıyor; rate limit; günlük örnekleme (§3) |
| **Ekşi Sözlük** | Login yok, Scrapling | Entry metni, yazar, favori sayısı, düzenlenme bilgisi | Var (dakika, TR saati) | Yazar sayfası var, kullanılmadı: sözlükte bot tahmini case'in odağı değil | `?day=` filtresi 404 verdi; aramada konu dışı başlıklar çıktı |
| TikTok (deneme) | Login yok, Playwright | Aramada **22 tarihli video** kaydı (API yanıtından) | Var (`createTime`) | Denenmedi | Etiket sayfası veri vermedi; metin çoğunlukla video açıklaması |
| Instagram (deneme) | Login yok | Hiç | – | – | Etiket sayfası `/popular/`'a yönlendi, arama **login duvarına** takıldı |

Deneme sonuçları `bench/social_probe.md` dosyasında. Oradaki "captcha" sütunu güvenilmez, çünkü sayfa kaynağında sadece kelime araması yapıyor. Kaynak ikilisini X + Ekşi seçtik. Gerekçeler: X metin tabanlı ve en zengin profil verisini veriyor. Ekşi ise tarihli ve **tam sayılabilen** tek kaynak (§3).

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

**Ortak kayıt** (`data/records.jsonl`) şu alanlardan oluşuyor: `source, url, text, published_at (TZ'li ya da null), collected_at (UTC), author (maskeli), query, extra`.
- **Tekrar temizliği:** `id = sha1(kaynak | kanonik URL)`. Takip parametreleri, `www` ve sondaki `/` temizleniyor. Aynı komut tekrar çalışınca kayıt eklenmiyor (upsert). İlk `collected_at` korunuyor, sadece boş alanlar dolduruluyor. Metni aynı ya da neredeyse aynı içerikler de analizde tek sayılıyor (3-kelime shingle Jaccard ≥ 0.8).
- **Eksik tarih:** Ekşi'de saat bilgisi yoksa `published_at=null`, gün bilgisi ise `extra.published_date` alanında tutuluyor. Tahmin yapılmıyor. Toplanan 570 kaydın hepsinde tarih vardı. Kural testlerle korunuyor.
- **Maskeleme:** Kullanıcı adları ve metin içindeki @mention'lar tuzlu SHA-256 ile maskeleniyor (`u_xxxxxxxxxx`). X URL'leri kullanıcı adı içermeyen `x.com/i/status/<id>` biçiminde.
- **Hacim:** Ekşi 187 entry. Son 14 günde 62; 9 firma başlığı + aramayla bulunan 13 aktif başlık üzerinden. X'te 383 tweet ve 48 profil var. Analize giren kısım: son 7 günde 109 tweet + 34 entry, önceki 7 günde 107 tweet + 28 entry.

**Sorun günlüğü.** Otomatik kısmı `data/issues.jsonl` dosyasında:

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

**Hesap profili ve gerçek/sahte tahmini** (`trend/profiles.py`): Kural tabanlı, her kural bir gerekçe cümlesi üretiyor.
- Hesap 30 günden yeniyse +2, 180 günden yeniyse +1
- Ömür boyu günde 20'den / 50'den fazla paylaşım: +1 / +2
- Son 20 paylaşımda tekrar oranı %30'dan / %50'den fazla: +1 / +2
- Takipçi < 10 ve takip > 200: +1
- Varsayılan profil fotoğrafı: +1
- Kullanıcı adı ≥ 4 haneli rakamla bitiyor: +1
- Etiket: ≥ 4 "bot olası", 2–3 "şüpheli".

**Sonuç:** 48 hesabın 45'i "gerçek olası", 3'ü "şüpheli" (ör. "hesap 25 günlük"; "varsayılan fotoğraf + rakamla biten ad"), hiçbiri "bot olası". Bot olası hesaplar analizde otomatik dışlanıyor. Bu çalıştırmada dışlanan hesap olmadı. **Sınır:** 20 tweetlik geçmiş ve basit eşikler, olsa olsa kaba spam'i yakalar; koordineli ama "normal görünen" hesapları yakalamaz.

## 5. Sinyal yöntemi ve belirsizlik

**Gruplama:** Her kayıt iki boyutta gruplanıyor.
- **tema:** 8 temalı kök-kelime sözlüğü. En çok eşleşen tema seçiliyor; kelime başı eşleşmesi kullanılıyor, böylece "zam" kökü "zaman"ı yakalamıyor.
- **firma:** Ekşi'de başlık slug'ından, X'te metinden çıkarılıyor.

Olası yanlış birleşmeler:
- Bir firma başlığında başka firmayı öven entry, başlık firmasına yazılıyor (ör. PTT başlığında "cargox daha kötü").
- "kurye" kelimesi, gecikmeden şikâyet eden bir metni de kurye davranışı temasına çekebiliyor.
- İçeriğin %65'i "diğer" temasında kalıyor. Bunlar belirli bir sorun söylemeyen, genel yorumlar.

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

Kurallardan sonra aynı veri "yükseliş yok / doğrulanamadı" sonucunu verdi. Bir yan etki de oldu: "gelmedi/gecikti" sorgusu önceki haftada rate limit yüzünden yalnız 4 gün kapsadığı için (4/7) analiz dışı kaldı. Bu da X'in tema sinyallerini zayıflatıyor.

**Testler:** Toplam 35 test, internet gerekmiyor (`python -m pytest`). Kapsadıkları:
- tekrar kayıt ve URL varyantları
- eksik tarih, TZ'siz tarihin reddedilmesi
- dönem sınırları, organik artış
- **30 kopya spam'in sahte artış yaratmaması** (ham +2, temiz < 1)
- bot hesabın dışlanması
- tek kaynak, az kayıt, tek gün ve dengesiz kapsama durumlarının "doğrulanamadı" vermesi
- kaydedilmiş HTML ve GraphQL fixture'larıyla parser'lar
- Ekşi'nin geriye sayfalamasının kesimde durması
- GraphQL URL ayrıştırmasının hiç hata fırlatmaması

## 6. İleriye bakış: LangGraph ve RAG

**LangGraph** toplama ve karar akışını bir durum makinesi olarak modellemek için uygun: `topla → kapsama kontrolü → (dengesizse) eksik günleri yeniden topla → grupla → puanla → (aday varsa) ikinci kaynakta hedefli doğrulama sorgusu → rapor`. Bugün elle yaptığımız "Kolay Gelsin'i X'te ayrıca ara" adımı, koşullu bir kenar olarak otomatikleşir. Rate limit beklemeleri ve yeniden denemeler de graf durumunda izlenebilir.

**RAG** iki yerde işe yarar:
- **Gruplama:** Kök-kelime sözlüğü yerine embedding ile benzer şikâyetleri geçmiş etiketli örneklere eşlemek. Bugün %65'i "diğer"de kalan içeriği anlamlı temalara ayırabilir.
- **Rapor:** Aday sinyal için geçmiş haftaların benzer konuşmalarını ve kanıt URL'lerini getirip "bu yeni mi, mevsimsel mi?" sorusunu kanıta dayalı yanıtlamak.

İki kullanımda da nihai karar bugünkü açıklanabilir eşiklerle verilmeli; LLM çıktısı kanıt URL'si olmadan kabul edilmemeli.

## 7. AI ile çalışma

**Araç:** Claude (Cowork). Case analizi, mimari, kodun büyük kısmı ve testler için kullanıldı. Kodu kendi PyCharm'ımda çalıştırdım, her adımın çıktısını geri verdim, Claude da gerektiğinde ham debug dosyalarını okuyup düzeltti.

**İşe yarayan yöntemler:**
1. İşi küçük adımlara bölmek: iskelet+testler → Ekşi → araç ölçümü → X → analiz → rapor.
2. Analiz çekirdeğini **canlı veri gelmeden önce** yapay veriyle test etmek (spam, eksik tarih, tek kaynak).
3. Canlı siteyi tek başlık/tek gün gibi küçük denemelerle yoklamak.
4. Hata olduğunda tahmin yürütmek yerine ham yanıtı kaydedip (`--save-html`) veriye bakmak.

**Doğrulama:**
- Her değişiklikten sonra `pytest`.
- `python -m trend stats` ile gün dağılımına bakmak.
- Her bulguyu URL'ye kadar izlemek.
- Şüpheli sonuçta (üç "yüksek güven" aday) veriyi açıp kaynağını kontrol etmek.

**AI'ın yanıldığı örnekler** (tam liste `AI_NOTLARI.md`'de, 8 madde):
- Ekşi `?day=` parametresinin çalışacağını **varsaydı**; canlı sitede 404 döndü.
- X tarih filtresini UTC sandı.
- Playwright dinleyicisinde hata fırlatan bir satır yazdı ve bu, profil kaydırmayı bozdu.
- En önemlisi: ilk analizde "yüksek güvenli" üç yükseliş raporladı. Bunlar kendi toplama sürecimizin ürünüydü.

Ders: AI kodu hızla yazıyor, ama canlı sistem hakkındaki varsayımları ve "iyi görünen" sonuçları küçük deneme ve ham veriyle doğrulamak gerekiyor.

**Etik not:** X ve Instagram kullanım koşulları otomatik veri toplamayı kısıtlıyor. Az veri, yan hesap ve maskeli teslim ile, yalnızca bu prototip için çalışıldı. Üretimde resmi API ya da lisanslı veri sağlayıcı kullanılmalı.
