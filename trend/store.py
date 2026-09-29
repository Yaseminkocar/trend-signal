from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .schema import Record


def load(path: Path) -> list[Record]:
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(Record.from_dict(json.loads(line)))
    return out


def save(path: Path, records: Iterable[Record]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(records, key=lambda r: (r.source, r.published_at or "", r.id))
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
    tmp.replace(path)


def upsert(path: Path, new: Iterable[Record]) -> tuple[int, int]:
    existing = {r.id: r for r in load(path)}
    added = dup = 0
    for r in new:
        old = existing.get(r.id)
        if old is None:
            existing[r.id] = r
            added += 1
            continue
        dup += 1
        if old.published_at is None and r.published_at is not None:
            old.published_at = r.published_at
        if old.author is None and r.author is not None:
            old.author = r.author
        for k, v in r.extra.items():
            old.extra.setdefault(k, v)
    save(path, existing.values())
    return added, dup
