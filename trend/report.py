from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .profiles import BotVerdict

STATUS_TR = {"yukselis_adayi": "YÜKSELİŞ ADAYI", "dogrulanamadi": "DOĞRULANAMADI",
             "yukselis_yok": "yükseliş yok"}


def write(result: dict, verdicts: list[BotVerdict], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    js = dict(result, groups=[asdict(g) for g in result["groups"]],
              bot_verdicts=[asdict(v) for v in verdicts])
    (out_dir / "signals.json").write_text(json.dumps(js, ensure_ascii=False, indent=2), encoding="utf-8")

    t = result["totals"]
    L = [f"# Sinyal özeti (asof {result['asof']})", "",
         f"- Son 7 gün: `{result['periods']['current'][0]}` -> `{result['periods']['current'][1]}`",
         f"- Önceki 7 gün: `{result['periods']['previous'][0]}` -> `{result['periods']['previous'][1]}`",
         f"- Kayıt: {t['records']} (son 7g: {t['current']}, önceki 7g: {t['previous']}, "
         f"yayın zamanı yok: {t['undated']}, dönem dışı: {t['outside_windows']}); "
         f"tekil içerik kümesi: {t['unique_clusters']}; hariç tutulan bot-olası hesap: {t['bot_authors_excluded']}",
         "- Gün kapsaması (kaynak: önceki/son): " + ", ".join(
             f"{k} {v['previous_days']}/{v['current_days']}" for k, v in sorted(result.get("coverage", {}).items())),
         "- Dengesiz kapsama yüzünden analiz dışı bırakılan sorgular: " + (", ".join(
             f"`{k}` ({v})" for k, v in result.get("excluded_queries", {}).items()) or "yok"),
         "", "| Grup | Önceki->Son (ham) | Önceki->Son (tekil) | Ham puan | Temiz puan | Tekrar etkisi | Yazar | Gün | Kaynak | Durum | Güven |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for g in result["groups"]:
        L.append(f"| {g.group} | {g.raw_previous}->{g.raw_current} | {g.unique_previous}->{g.unique_current} | "
                 f"{g.raw_score:+.2f} | {g.clean_score:+.2f} | {g.duplicate_effect:+.2f} | {g.authors_current} | "
                 f"{g.active_days_current} | {', '.join(g.sources_current) or '-'} | {STATUS_TR[g.status]} | {g.confidence} |")

    cands = [g for g in result["groups"] if g.group != "TUMU" and g.status != "yukselis_yok"][:3]
    L += ["", "## Aday sinyaller (en fazla 3)", ""]
    if not cands:
        L.append("Eşiği geçen grup yok: **yükseliş bulunamadı** (bu da geçerli bir sonuç).")
    for g in cands:
        L += [f"### {g.group} - {STATUS_TR[g.status]} (güven: {g.confidence})",
              f"- Tekil içerik: önceki 7g **{g.unique_previous}** -> son 7g **{g.unique_current}** "
              f"(temiz puan {g.clean_score:+.2f}, ham {g.raw_score:+.2f})",
              f"- Günlere dağılım: {g.daily_current}",
              "- Kontroller: " + "; ".join(("[ok] " if c.passed else "[eksik] ") + c.detail for c in g.checks)]
        if g.missing:
            L.append("- **Eksik kanıt:** " + "; ".join(g.missing))
        L.append("- Kanıt:")
        for e in g.evidence:
            L.append(f"  - [{e['source']}] {e['published_at']} - {e['url']} - '{e['text'][:100]}'")
        L.append("")

    if verdicts:
        from collections import Counter
        c = Counter(v.label for v in verdicts)
        L += ["## Hesap tahminleri", "", f"{dict(c)}", "",
              "| Yazar (maskeli) | Puan | Etiket | Gerekçe |", "|---|---|---|---|"]
        for v in sorted(verdicts, key=lambda v: -v.score)[:15]:
            L.append(f"| {v.author} | {v.score} | {v.label} | {'; '.join(v.reasons)} |")

    md = out_dir / "signals.md"
    md.write_text("\n".join(L) + "\n", encoding="utf-8")
    return md
