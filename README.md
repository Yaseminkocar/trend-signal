# trend-signal: kargo/teslimat erken trend sinyali

Ekşi Sözlük, X, TikTok ve Instagram'dan "kargo/teslimat" konuşmalarını toplayan, son 7 günü önceki 7 günle kıyaslayan,
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

## Çalıştırma

**1) Testler** — internet gerekmez, canlı siteye bağlı değil:

```bash
python -m pytest
```

**2) Analizi repodaki veriyle tekrar üret** — internet gerekmez. Çıktı `output/signals.md` ve `output/signals.json`
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
verisi toplanır ama sinyal hesabı varsayılan olarak yalnız Ekşi + X ile yapılır (gerekçe: RAPOR.md §5). Tüm kaynaklarla:

```bash
python -m trend analyze --asof 2026-09-30T00:00:00+03:00 --sources eksi,x,instagram,tiktok
```

**4) Araç karşılaştırması ve TikTok/Instagram denemesi** — sonuçlar `bench/results.md` ve `bench/social_probe.md`:

```bash
pip install -r requirements-bench.txt
python bench/compare_tools.py
python bench/probe_social.py
```

Aynı toplama komutunu tekrar çalıştırmak kayıtları çoğaltmaz: anahtar `sha1(kaynak | kanonik URL)`.

## Veri (repoda, kullanıcı adları maskeli)

| Dosya | İçerik |
|---|---|
| `data/records.jsonl` | Tüm kayıtlar (669: Ekşi 187, X 383, Instagram 90, TikTok 9): `source, url, text, published_at (TZ'li / null), collected_at, author, query, extra` |
| `data/sample.csv` | Küçük örnek: 25 Ekşi + 25 X kaydı |
| `data/profiles.jsonl` | 48 X hesap profili (hesap yaşı, sayaçlar, son 20 tweet) |
| `data/issues.jsonl` | Otomatik sorun günlüğü |

## Yapı

```
trend/
  schema.py        ortak kayıt, kanonik URL, normalizasyon
  store.py         idempotent JSONL upsert
  privacy.py       tuzlu hash ile kullanıcı adı / @mention maskeleme
  fetchers.py      requests | scrapling | playwright, aynı arayüz
  collectors/      eksi.py (HTML), x.py (GraphQL yanıt dinleme; twikit yedek), social.py (TikTok, Instagram)
  profiles.py      açıklanabilir bot puanı
  analysis/        grouping.py (tema/firma + yakın-tekrar), signal.py (7/7 kıyas, kontroller)
  report.py, cli.py
tests/             38 offline test + fixture'lar
bench/             araç karşılaştırması, TikTok/IG denemesi
```

Ayarlar (sorgular, tema sözlüğü, eşikler) tek dosyada: `trend/config.py`.
