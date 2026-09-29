from __future__ import annotations

import json
from collections import Counter

from . import config
from .schema import now_utc_iso


def log_issue(source: str, kind: str, detail: str, handling: str) -> None:
    config.ISSUE_LOG.parent.mkdir(parents=True, exist_ok=True)
    row = {"at": now_utc_iso(), "source": source, "kind": kind, "detail": detail[:300],
           "handling": handling}
    with config.ISSUE_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"  [sorun] {source}/{kind}: {detail[:120]} -> {handling}")


def summarize() -> Counter:
    if not config.ISSUE_LOG.exists():
        return Counter()
    rows = [json.loads(l) for l in config.ISSUE_LOG.read_text(encoding="utf-8").splitlines() if l]
    return Counter((r["source"], r["kind"]) for r in rows)
