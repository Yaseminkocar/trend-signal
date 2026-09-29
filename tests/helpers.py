from __future__ import annotations

from datetime import datetime, timedelta, timezone

from trend.schema import Record

ASOF = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
COLLECTED = "2026-09-29T12:00:00+00:00"


def rec(n: int, days_ago: float | None, text: str | None = None, source: str = "x",
        author: str | None = None) -> Record:
    pub = None if days_ago is None else (ASOF - timedelta(days=days_ago)).isoformat()
    return Record(
        source=source,
        url=f"https://example.com/{source}/{n}",
        text=text or f"yurtiçi kargo paketim gecikti {n} numaralı şikayet farklı cümle {n * 7}",
        published_at=pub,
        collected_at=COLLECTED,
        author=author or f"u_{n % 50:04d}",
    )
