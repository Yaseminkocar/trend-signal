from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .. import config
from ..schema import Record, normalize_text


def _needle(kw: str) -> str:
    n = " " + normalize_text(kw)
    return n + " " if kw.endswith(" ") else n


def _match(text_norm: str, keywords: Iterable[str]) -> list[str]:
    padded = f" {text_norm} "
    return [kw.strip() for kw in keywords if _needle(kw) in padded]


def assign_theme(text: str, themes: dict[str, list[str]] | None = None) -> tuple[str, list[str]]:
    themes = themes or config.THEMES
    norm = normalize_text(text)
    best, best_hits = "diger", []
    for name, kws in themes.items():
        hits = _match(norm, kws)
        if len(hits) > len(best_hits):
            best, best_hits = name, hits
    return best, best_hits


def detect_brands(text: str) -> list[str]:
    norm = normalize_text(text)
    return [name for name, kws in config.BRANDS.items() if _match(norm, kws)]


def assign_brand(r: Record) -> str:
    topic_url = (r.extra or {}).get("topic_url") or ""
    slug = topic_url.rsplit("/", 1)[-1]
    for key, name in config.BRAND_SLUGS.items():
        if slug.startswith(key):
            return name
    found = detect_brands(r.text)
    if len(found) == 1:
        return found[0]
    return "coklu_firma" if found else "firma_belirsiz"


def _shingles(text: str, k: int = 3) -> set[str]:
    words = normalize_text(text).split()
    if len(words) < k:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i:i + k]) for i in range(len(words) - k + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def near_duplicate_clusters(records: list[Record], threshold: float = 0.8) -> dict[str, str]:
    parent = {r.id: r.id for r in records}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    sh = {r.id: _shingles(r.text) for r in records}
    by_norm: dict[str, list[str]] = defaultdict(list)
    for r in records:
        by_norm[normalize_text(r.text)].append(r.id)
    for ids in by_norm.values():
        for other in ids[1:]:
            union(ids[0], other)
    ids = [r.id for r in records]
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            if find(ids[i]) != find(ids[j]) and jaccard(sh[ids[i]], sh[ids[j]]) >= threshold:
                union(ids[i], ids[j])
    return {i: find(i) for i in ids}
