from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trend.analysis.ads import is_ad


def main() -> None:
    records = {}
    for line in (ROOT / "data/kargo/records.jsonl").read_text(encoding="utf-8").split("\n"):
        if not line.strip():
            continue
        r = json.loads(line)
        records[r["url"]] = r["text"]
    cm, errors = Counter(), []
    with open(ROOT / "data/kargo/ad_labels.csv", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["url"]]
    for row in rows:
        pred, why = is_ad(records[row["url"]])
        gold = row["etiket"] == "ticari"
        cm[(row["source"], gold, pred)] += 1
        if gold != pred:
            errors.append((row, pred, why))
    tp = sum(v for (s, g, p), v in cm.items() if g and p)
    fp = sum(v for (s, g, p), v in cm.items() if not g and p)
    fn = sum(v for (s, g, p), v in cm.items() if g and not p)
    tn = sum(v for (s, g, p), v in cm.items() if not g and not p)
    precision, recall = tp / (tp + fp), tp / (tp + fn)
    L = ["# Ilan / kurumsal gonderi filtresi: elle etiketlenmis veriyle olcum", "",
         f"Veri: `data/kargo/ad_labels.csv` ({len(rows)} gonderi: "
         f"{sum(r['source'] == 'instagram' for r in rows)} Instagram, {sum(r['source'] == 'tiktok' for r in rows)} TikTok)", "",
         "| | tahmin: ticari | tahmin: bireysel |", "|---|---|---|",
         f"| etiket: ticari | {tp} | {fn} |", f"| etiket: bireysel | {fp} | {tn} |", "",
         f"- Kesinlik (ticari dedigimizin gercekten ticari olma orani): {precision:.2f}",
         f"- Duyarlilik (ticari gonderilerin yakalanma orani): {recall:.2f}",
         f"- Bireysel gonderilerin korunma orani: {tn / (tn + fp):.2f}", "",
         "## Hatalar", "", "| Etiket | Tahmin | Gerekce | Metin |", "|---|---|---|---|"]
    for row, pred, why in errors:
        text = row["metin"][:80].replace("|", "/")
        L.append(f"| {row['etiket']} | {'ticari' if pred else 'bireysel'} | {', '.join(why) or '-'} | {text} |")
    out = ROOT / "bench/ad_filter_eval.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"kesinlik {precision:.2f}, duyarlilik {recall:.2f} -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
