# trend-signal: erken trend sinyali

Bir tüketici konusu hakkında Ekşi Sözlük, X, TikTok ve Instagram'dan konuşmaları toplayan, son 7 günü önceki 7 günle
kıyaslayan ve "yükseliş adayı", "doğrulanamadı" ya da "yükseliş yok" diye açıklanabilir bir sonuç veren prototip.
Kopyalar, satış ilanları, bot olası hesaplar ve toplama sürecinden kaynaklanan sahte artışlar ayıklanır.

Örnek konu kargo/teslimat. Bulgular, kararlar ve yöntem `RAPOR.md` (ya da `RAPOR.pdf`) dosyasında.

## 1. Hızlı başlangıç (internet ve hesap gerekmez)

Python 3.12 gerekir. Proje klasöründe sırayla:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest
```

Son komut `64 passed` yazmalı. Testler canlı sitelere bağlanmaz.

Repodaki kargo verisiyle analizi tekrar üretmek için:

```bash
python -m trend analyze --asof 2026-09-30T00:00:00+03:00
```

Terminalde grup tablosu çıkar: hasar/kayıp ve müşteri hizmetleri temaları "yukselis_adayi", Kolay Gelsin
"dogrulanamadi". Ayrıntılı rapor `output/kargo/signals.md` dosyasına yazılır ve teslimdeki
`reports/signals_2026-09-30.md` ile aynıdır.

## 2. Arayüz (önerilen)

Kolay kullanım için arayüzle çalıştırmanız önerilir. Arayüz isteğe bağlıdır; kurulmasa da her şey komut satırından çalışır.

```bash
pip install -r requirements-ui.txt
streamlit run app.py
```

Tarayıcıda `http://localhost:8501` açılır. Denemek için:

1. Konu kutusuna `kargo` yazın.
2. Sol menüde kaynak olarak Ekşi Sözlük ve X seçili kalsın, dönem 7 gün olsun.
3. **Kayıtlı veriyle analiz et** düğmesine basın. İnternet gerekmez.

Sonuç ekranında aday sinyaller, her birinin sağladığı ve eksik kalan kontroller, kanıt linkleri, günlere göre içerik
grafiği ve bütün grupların tablosu görünür. Tablodaki "eksik kanıt" sütunu, bir grubun neden "doğrulanamadı"
olduğunu söyler. Rapor `.md` ya da `.json` olarak indirilebilir. Arayüzü kapatmak için terminalde Ctrl+C.

Sol menüdeki ayarlar:

| Ayar | Ne işe yarar |
|---|---|
| Kaynaklar | Hangi sitelerden toplanacağı ve analize hangilerinin gireceği |
| Karşılaştırma | Son 7, 14 ya da 21 gün, önceki aynı uzunluktaki dönemle kıyaslanır |
| Son gün | Kıyasın biteceği gün; kayıtlı veri varsa varsayılan olarak verideki son gün |
| Filtreler | Konu dışı içerik, ilan ve kurumsal paylaşım, bot olası hesap filtreleri; yükseliş için en az kaç kaynak gerektiği |
| Hızlı toplama | Açıksa toplama birkaç dakika sürer ama X'in eski günleri boş kalabilir; kapalıysa X 15-30 dakika sürer |

## 3. Yeni bir konu aramak (internet gerekir)

### Hazırlık (bir kez)

```bash
playwright install chromium
cp .env.example .env
```

`.env` dosyasına X için bir yan hesabın `auth_token` ve `ct0` cookie'lerini, Instagram için `IG_SESSIONID` değerini
yazın. Bu dosya git'e girmez. Hangi kaynağın ne istediği:

| Kaynak | Giriş gerekir mi | Not |
|---|---|---|
| Ekşi Sözlük | Hayır | Her zaman çalışır |
| X | Evet (`.env` içinde cookie) | Cookie yoksa X atlanır, diğer kaynaklarla devam edilir |
| TikTok | Hayır | Eski içerik çok geldiği için az kayıt kalır |
| Instagram | Evet (`IG_SESSIONID`) | Satış ilanları analizden önce otomatik ayıklanır |

### Arayüzden

1. Konu kutusuna konuyu yazın, ör. `akaryakıt zammı`.
2. İsterseniz "Yeni konu için anahtar kelimeler ve markalar" bölümüne virgülle kelime ve marka yazın,
   ör. `benzin zammı, motorin zammı` ve `Opet, Shell`. Boş bırakılırsa konu adı kullanılır.
3. **Veri topla ve analiz et** düğmesine basın. İlerleme hem ekranda hem terminalde görünür.

Konu dosyası `topics/<konu>.json`, veri `data/<konu>/` altında oluşur. Aynı konu tekrar arandığında kayıtlar çoğalmaz.

### Komut satırından

Tek komutla (konu dosyası yoksa oluşturur, Ekşi ve X'ten toplar, analiz eder):

```bash
python -m trend run "akaryakıt zammı" --keywords "benzin zammı,motorin zammı" --brands "Opet,Shell"
```

Dönem uzunluğu için `--window 14`, farklı kaynaklar için `--collect eksi,x,tiktok` eklenebilir.

### İpuçları

- **Anahtar kelime:** Ekşi başlık adıyla birebir aynı olması gerekmez. Tam ifade bulunamazsa kelimelerin hepsini içeren
  aktif başlıklar alınır ("bmw 3" yazınca "bmw 3 serisi" bulunur).
- **Uzun toplama:** Hızlı mod kapalıyken X toplaması 15-30 dakika sürebilir. Bu kadar uzun toplamalar için terminal
  daha güvenlidir: `python -m trend --topic akaryakit_zammi collect x`, bitince arayüzde "Kayıtlı veriyle analiz et".
- **"Doğrulanamadı" sonucu:** Artış var ama bir kontrol eksik demektir; tablodaki "eksik kanıt" sütunu hangisi
  olduğunu söyler. En sık neden, konuşmanın tek bir güne yığılmasıdır (bir tanıtım ya da zam günü). Konuşma birkaç
  güne yayılınca aynı arama "yükseliş adayı" verebilir.
- **Analize kayıt kalmadıysa:** Nedenler ekranın başında yazar. Genellikle X'in önceki dönemi boş kalmıştır (hızlı modu
  kapatın ya da daha kısa dönem seçin) veya Ekşi seçilmemiştir.
- **Denemeleri repoya eklememek için:** commit'ten önce `git status` ile bakın, deneme konularının `data/`, `output/` ve
  `topics/` altındaki dosyalarını silin.

## 4. Komut satırı başvurusu

| Komut | Ne yapar |
|---|---|
| `python -m pytest` | Offline testleri çalıştırır |
| `python -m trend analyze --asof 2026-09-30T00:00:00+03:00` | Kayıtlı veriyle analiz; `--window 14`, `--sources eksi,x,instagram,tiktok` alabilir |
| `python -m trend collect eksi` | Ekşi'den son 14 günü toplar |
| `python -m trend collect x` | X'ten son 14 günü toplar (cookie gerekir) |
| `python -m trend collect x --fill-gaps` | X'te yalnız boş kalan günleri yeniden toplar |
| `python -m trend collect tiktok` ya da `collect instagram` | TikTok ve Instagram'dan toplar |
| `python -m trend stats` | Kaynak ve gün dağılımı, sorun günlüğü özeti |
| `python -m trend run "konu"` | Konu oluşturur, toplar ve analiz eder |
| `python -m trend topics` | Kayıtlı konuları listeler |
| `python -m trend --topic <konu> ...` | Herhangi bir komutu başka bir konu için çalıştırır |
| `python -m trend --topic <konu> collect eksi --until 2026-08-14` | Geçmiş bir dönemi toplar; analizde `--asof 2026-08-15T00:00:00+03:00` |

Araç karşılaştırması ve ilan filtresi ölçümü (sonuçlar `bench/` altında):

```bash
pip install -r requirements-bench.txt
python bench/compare_tools.py
python bench/eval_ads.py
```

## 5. Repodaki veri

Kullanıcı adları maskeli, telefon numaraları `[tel]` ile değiştirilmiş.

| Dosya | İçerik |
|---|---|
| `data/kargo/records.jsonl` | Tüm kayıtlar (669: Ekşi 187, X 383, Instagram 90, TikTok 9). Alanlar: `source, url, text, published_at, collected_at, author, query, extra` |
| `data/kargo/sample.csv` | Küçük örnek veri: 25 Ekşi, 25 X kaydı |
| `data/kargo/profiles.jsonl` | 48 X hesap profili (hesap yaşı, sayaçlar, son 20 tweet) |
| `data/kargo/issues.jsonl` | Toplama sırasında otomatik tutulan sorun günlüğü |
| `data/kargo/ad_labels.csv` | İlan filtresini ölçmek için etiketlenmiş 99 Instagram/TikTok gönderisi |
| `reports/` | Teslimdeki analiz çıktıları |

## 6. Proje yapısı

```
app.py             Streamlit arayüzü
trend/
  cli.py           komut satırı
  pipeline.py      filtreler ve analiz (arayüz ve komut satırı ortak kullanır)
  collectors/      eksi.py, x.py, social.py (TikTok, Instagram)
  analysis/        signal.py (dönem kıyası ve kontroller), grouping.py (tema, firma, kopyalar), ads.py (ilan filtresi)
  profiles.py      bot tahmini
  schema.py, store.py, privacy.py, fetchers.py, topics.py, report.py, config.py
topics/            konu ayarları (kargo.json, elektrikli_arac.json)
tests/             offline testler
bench/             araç karşılaştırması, TikTok/Instagram denemesi, ilan filtresi ölçümü
requirements.txt   ana bağımlılıklar (sürümler sabit); -ui arayüz, -bench araç karşılaştırması için
```

Eşikler ve konudan bağımsız ayarlar `trend/config.py` dosyasında.
