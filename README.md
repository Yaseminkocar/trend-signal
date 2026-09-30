# trend-signal: erken trend sinyali (örnek konu: kargo/teslimat)

Ekşi Sözlük, X, TikTok ve Instagram'dan bir tüketici konusundaki konuşmaları toplayan, son 7 günü önceki 7 günle kıyaslayan,
kopyaları, bot olası hesapları ve kapsama dengesizliğini ayıklayarak açıklanabilir bir sinyal puanı üreten prototip.
Bulgular ve kararlar `RAPOR.md` dosyasında, AI ile çalışma notları `AI_NOTLARI.md` dosyasında.

## Kurulum (Python 3.12, macOS/Linux)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Yalnız X'ten yeniden veri toplamak için ek olarak `playwright install chromium` çalıştırın ve `cp .env.example .env`
ile oluşan dosyaya yan hesabın `auth_token` / `ct0` cookie'lerini yazın.

## Önerilen: arayüzle kullanım

Kolay kullanım için arayüzle çalıştırmanız önerilir. Arayüz isteğe bağlıdır; aşağıdaki komut satırı akışı ve testler
onsuz da çalışır.

```bash
pip install -r requirements-ui.txt
streamlit run app.py
```

Tarayıcıda açılan sayfada konu yazılır, kaynaklar (Ekşi, X, Instagram, TikTok) ve karşılaştırma dönemi (7, 14 ya da
21 gün) seçilir, filtreler (konu dışı içerik, ilan/kurumsal paylaşım, bot olası hesap, en az kaynak sayısı) açılıp
kapatılabilir. İnternet ve hesap gerektirmeden denemek için konu kutusuna `kargo` yazıp "Kayıtlı veriyle analiz et" düğmesine
basın: repodaki veriyle `reports/signals_2026-09-30.md` ile aynı sonuç görünür. Sonuç ekranında aday sinyaller, kontroller,
kanıt linkleri, günlere göre içerik grafiği ve tüm grupların tablosu var; rapor `.md` ve `.json` olarak indirilebilir.
Yeni konuda X toplaması varsayılan olarak hızlı modda çalışır (günde en fazla 10 gönderi, 10 profil, boş gün için bekleme yok;
birkaç dakika). Hızlı mod kapatılırsa sonuç daha sağlam olur ama toplama 15-30 dakika sürebilir. Komut satırında karşılığı
`collect x --per-day 10 --profiles 10 --no-retry`.

## Çalıştırma (komut satırı)

**1) Testler** — internet gerekmez, canlı siteye bağlı değil:

```bash
python -m pytest
```

**2) Analizi repodaki veriyle tekrar üret** — internet gerekmez. Çıktı `output/kargo/signals.md` ve `output/kargo/signals.json`
dosyalarına yazılır; teslimdeki kopyası `reports/signals_2026-09-30.*`:

```bash
python -m trend analyze --asof 2026-09-30T00:00:00+03:00
```

**3) Veriyi yeniden topla** — internet gerekir. Sırasıyla: Ekşi (Scrapling; 9 firma başlığı + aramayla keşif, son 15 gün),
X (Playwright + cookie; günlük örnekleme + 30 profil), X'te yalnız boş kalan (sorgu, gün) çiftlerini yeniden deneme,
kaynak/gün dağılımı ve sorun günlüğü özeti, analiz (asof = şimdi):

```bash
python -m trend collect eksi
python -m trend collect x
python -m trend collect x --fill-gaps
python -m trend collect tiktok
python -m trend collect instagram
python -m trend stats
python -m trend analyze
```

Instagram girişsiz çalışmaz; `.env` içindeki `IG_SESSIONID` ile yan hesabın oturumu kullanılır. TikTok ve Instagram
verisi toplanır ama sinyal hesabı varsayılan olarak yalnız Ekşi + X ile yapılır (gerekçe: RAPOR.md §5). Bu iki kaynaktaki
satış ilanı ve kurumsal paylaşımlar analizden önce `trend/analysis/ads.py` ile ayıklanır. Tüm kaynaklarla:

```bash
python -m trend analyze --asof 2026-09-30T00:00:00+03:00 --sources eksi,x,instagram,tiktok
```

**4) Araç karşılaştırması, TikTok/Instagram denemesi, ilan filtresi ölçümü** — sonuçlar `bench/results.md`,
`bench/social_probe.md` ve `bench/ad_filter_eval.md`:

```bash
pip install -r requirements-bench.txt
python bench/compare_tools.py
python bench/probe_social.py
python bench/eval_ads.py
```

Aynı toplama komutunu tekrar çalıştırmak kayıtları çoğaltmaz: anahtar `sha1(kaynak | kanonik URL)`.

## Başka bir konu ya da başka bir tarih

Konuya özgü her şey (Ekşi başlıkları, X/TikTok/Instagram sorguları, alaka kelimeleri, tema sözlüğü, marka listesi)
`topics/<konu>.json` dosyasında. Kod konudan bağımsız; her konunun verisi `data/<konu>/`, çıktısı `output/<konu>/` altına yazılır.
Varsayılan konu `kargo`. Örnek ikinci konu: `topics/elektrikli_arac.json`.

**Tek komutla:** konu dosyası yoksa oluşturur, veriyi Ekşi ve X'ten toplar ve analiz eder. `.env` içinde X cookie'leri yoksa ya da X hata verirse X atlanır, analiz Ekşi ile devam eder:

```bash
python -m trend run "elektrikli scooter"
python -m trend run "Kahve zincirleri" --keywords "filtre kahve,kahve fiyatı" --brands "Starbucks,Kahve Dünyası" --collect eksi,x,tiktok
```

Sonuçları iyileştirmek için oluşan `topics/<konu>.json` dosyasındaki sorgular ve temalar gözden geçirilip komut tekrar çalıştırılır
(kayıtlar çoğalmaz).

Adım adım: anahtar kelime ve markalardan başlangıç dosyası üretilir, sonra elle gözden geçirilir:

```bash
python -m trend init-topic kahve --label "Kahve zincirleri" --keywords "filtre kahve,kahve fiyatı" --brands "Starbucks,Kahve Dünyası"
python -m trend topics
python -m trend --topic kahve collect eksi
python -m trend --topic kahve analyze
```

Başka dönem uzunluğu: `--window 14` son 14 günü önceki 14 günle kıyaslar (`analyze` ve `run` komutlarında).

Başka tarih: analizde `--asof` kıyas anını, toplamada `--until` pencerenin son gününü belirler
(ör. 1-14 Ağustos için `--until 2026-08-14 --days 14`):

```bash
python -m trend --topic elektrikli_arac collect eksi --until 2026-08-14
python -m trend --topic elektrikli_arac analyze --asof 2026-08-15T00:00:00+03:00
```

Sınır: Ekşi'de başlık başına en fazla 30 sayfa geriye gidilir; çok eski ya da çok yoğun dönemlerde `EKSI_MAX_PAGES_PER_TOPIC`
artırılmalı. X ve Instagram hesap oturumu ister.

## Veri (repoda, kullanıcı adları maskeli)

| Dosya | İçerik |
|---|---|
| `data/kargo/records.jsonl` | Tüm kayıtlar (669: Ekşi 187, X 383, Instagram 90, TikTok 9): `source, url, text, published_at (TZ'li / null), collected_at, author, query, extra` |
| `data/kargo/sample.csv` | Küçük örnek: 25 Ekşi + 25 X kaydı |
| `data/kargo/profiles.jsonl` | 48 X hesap profili (hesap yaşı, sayaçlar, son 20 tweet) |
| `data/kargo/issues.jsonl` | Otomatik sorun günlüğü |
| `data/kargo/ad_labels.csv` | 99 Instagram/TikTok gönderisi için ticari/bireysel etiketleri (ilan filtresi ölçümü) |

## Yapı

```
trend/
  schema.py        ortak kayıt, kanonik URL, normalizasyon
  store.py         idempotent JSONL upsert
  privacy.py       tuzlu hash ile kullanıcı adı / @mention maskeleme
  fetchers.py      requests | scrapling | playwright, aynı arayüz
  collectors/      eksi.py (HTML), x.py (GraphQL yanıt dinleme; twikit yedek), social.py (TikTok, Instagram)
  profiles.py      açıklanabilir bot puanı
  analysis/        grouping.py (tema/firma + yakın-tekrar), signal.py (7/7 kıyas, kontroller), ads.py (ilan filtresi)
  topics.py        konu dosyası üretimi (init-topic)
  pipeline.py      filtreler + analiz (komut satırı ve arayüz ortak kullanır)
  report.py, cli.py
app.py             Streamlit arayüzü
topics/            konu ayarları (kargo.json, elektrikli_arac.json)
tests/             60 offline test + fixture'lar
bench/             araç karşılaştırması, TikTok/IG denemesi
```

Konudan bağımsız ayarlar (eşikler, günlük üst sınır, sinyal kaynakları): `trend/config.py`.
