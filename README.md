# trend-signal: kargo/teslimat erken trend sinyali

Ekşi Sözlük ve X'ten "kargo/teslimat" konuşmalarını toplayan, son 7 günü önceki 7 günle kıyaslayan,
kopyaları, bot olası hesapları ve kapsama dengesizliğini ayıklayarak açıklanabilir bir sinyal puanı üreten prototip.
Bulgular ve kararlar `RAPOR.md` dosyasında, AI ile çalışma notları `AI_NOTLARI.md` dosyasında.

## Kurulum (Python 3.12, macOS/Linux)

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium          # yalnız X toplamak için gerekli
cp .env.example .env                 # yalnız X toplamak için: yan hesabın auth_token / ct0 cookie'leri
```

## Çalıştırma

```bash
# 1) Testler: internet gerekmez, canlı siteye bağlı değil
python -m pytest

# 2) Analizi repodaki örnek veriyle tekrar üret (internet gerekmez)
python -m trend analyze --asof 2026-09-30T00:00:00+03:00
#    → output/signals.md + output/signals.json (teslimdeki kopya: reports/signals_2026-09-30.*)

# 3) Veriyi yeniden topla (internet gerekir)
python -m trend collect eksi                     # Scrapling; 9 firma başlığı + aramayla keşif, son 15 gün
python -m trend collect x                        # Playwright + cookie; günlük örnekleme + 30 profil
python -m trend collect x --fill-gaps            # yalnız boş kalan (sorgu, gün) çiftlerini yeniden dene
python -m trend stats                            # kaynak/gün dağılımı + sorun günlüğü özeti
python -m trend analyze                          # asof = şimdi

# Araç karşılaştırması ve TikTok/Instagram denemesi
pip install -r requirements-bench.txt
python bench/compare_tools.py                    # → bench/results.md
python bench/probe_social.py                     # → bench/social_probe.md
```

Aynı toplama komutunu tekrar çalıştırmak kayıtları çoğaltmaz: anahtar `sha1(kaynak | kanonik URL)`.

## Veri (repoda, kullanıcı adları maskeli)

| Dosya | İçerik |
|---|---|
| `data/records.jsonl` | Tüm kayıtlar (570): `source, url, text, published_at (TZ'li / null), collected_at, author, query, extra` |
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
  collectors/      eksi.py (HTML), x.py (GraphQL yanıt dinleme; twikit yedek)
  profiles.py      açıklanabilir bot puanı
  analysis/        grouping.py (tema/firma + yakın-tekrar), signal.py (7/7 kıyas, kontroller)
  report.py, cli.py
tests/             35 offline test + fixture'lar
bench/             araç karşılaştırması, TikTok/IG denemesi
```

Ayarlar (sorgular, tema sözlüğü, eşikler) tek dosyada: `trend/config.py`.
