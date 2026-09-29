from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Optional

from .. import config
from ..schema import Record
from .grouping import assign_carrier, assign_theme, near_duplicate_clusters


@dataclass
class Check:
    name: str
    passed: bool
    detail: str


@dataclass
class GroupSignal:
    group: str
    raw_current: int
    raw_previous: int
    unique_current: int
    unique_previous: int
    raw_score: float
    clean_score: float
    duplicate_effect: float
    authors_current: int
    sources_current: list[str]
    active_days_current: int
    max_day_share: float
    daily_current: dict[str, int]
    status: str
    confidence: str
    checks: list[Check] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)


def log_ratio(cur: int, prev: int) -> float:
    return round(math.log2((cur + 1) / (prev + 1)), 3)


def split_periods(records: list[Record], asof: datetime):
    cur_start, prev_start = asof - timedelta(days=7), asof - timedelta(days=14)
    cur, prev, undated, older = [], [], [], []
    for r in records:
        t = r.published_dt
        if t is None:
            undated.append(r)
        elif cur_start <= t < asof:
            cur.append(r)
        elif prev_start <= t < cur_start:
            prev.append(r)
        else:
            older.append(r)
    return cur, prev, undated, older


def _unique_count(rs: list[Record], cluster: dict[str, str], bots: set[str]) -> int:
    return len({cluster[r.id] for r in rs if not (r.author and r.author in bots)})


def coverage(records: list[Record], asof: datetime) -> dict[str, dict[str, int]]:
    cur, prev, _, _ = split_periods(records, asof)
    out: dict[str, dict[str, int]] = {}
    for label, rs in (("current_days", cur), ("previous_days", prev)):
        for r in rs:
            out.setdefault(r.source, {"current_days": 0, "previous_days": 0})
        days = defaultdict(set)
        for r in rs:
            days[r.source].add(r.published_dt.astimezone(config.TR_TZ).date())
        for src, ds in days.items():
            out[src][label] = len(ds)
    return out


SAMPLED_SOURCES = {"x", "tiktok", "instagram"}


def coverage_check(cov: dict[str, dict[str, int]]) -> Check:
    bad = [f"{s}: önceki {c['previous_days']} gün / son {c['current_days']} gün"
           for s, c in sorted(cov.items())
           if s in SAMPLED_SOURCES
           and min(c["current_days"], c["previous_days"]) < 0.6 * max(c["current_days"], c["previous_days"])]
    return Check("kapsama_dengesi", not bad,
                 "dönemler arası gün kapsaması dengeli" if not bad else "dengesiz kapsama: " + "; ".join(bad))


def balance_sampled(records: list[Record], cap: int) -> tuple[list[Record], int]:
    groups: dict[tuple, list[Record]] = defaultdict(list)
    keep: list[Record] = []
    for r in records:
        if r.source in SAMPLED_SOURCES and r.published_at:
            groups[(r.query, r.published_dt.astimezone(config.TR_TZ).date())].append(r)
        else:
            keep.append(r)
    dropped = 0
    for rs in groups.values():
        rs.sort(key=lambda r: r.id)
        keep.extend(rs[:cap]); dropped += max(len(rs) - cap, 0)
    return keep, dropped


def drop_unbalanced_queries(records: list[Record], asof: datetime) -> tuple[list[Record], dict[str, str]]:
    cur_start, prev_start = asof - timedelta(days=7), asof - timedelta(days=14)
    days: dict[tuple, dict[str, set]] = defaultdict(lambda: {"cur": set(), "prev": set()})
    for r in records:
        if r.source in SAMPLED_SOURCES and r.published_at:
            t = r.published_dt
            d = t.astimezone(config.TR_TZ).date()
            if cur_start <= t < asof:
                days[(r.source, r.query)]["cur"].add(d)
            elif prev_start <= t < cur_start:
                days[(r.source, r.query)]["prev"].add(d)
    excluded = {}
    for (src, q), dd in days.items():
        c, p = len(dd["cur"]), len(dd["prev"])
        if min(c, p) < 0.6 * max(c, p):
            excluded[f"{src}:{q}"] = f"önceki {p} gün / son {c} gün"
    kept = [r for r in records if not (r.source in SAMPLED_SOURCES and f"{r.source}:{r.query}" in excluded)]
    return kept, excluded


def analyze_group(name: str, records: list[Record], asof: datetime,
                  cluster: dict[str, str], bots: set[str], extra_checks: Optional[list[Check]] = None) -> GroupSignal:
    cur, prev, _, _ = split_periods(records, asof)
    u_cur, u_prev = _unique_count(cur, cluster, bots), _unique_count(prev, cluster, bots)
    raw_s, clean_s = log_ratio(len(cur), len(prev)), log_ratio(u_cur, u_prev)

    clean_cur = [r for r in cur if not (r.author and r.author in bots)]
    authors = {r.author for r in clean_cur if r.author}
    sources = sorted({r.source for r in clean_cur})
    days = Counter(r.published_dt.astimezone(config.TR_TZ).date().isoformat() for r in clean_cur)
    max_share = round(max(days.values()) / sum(days.values()), 2) if days else 0.0

    checks = [
        Check("yeterli_kayit", u_cur >= config.MIN_UNIQUE_CURRENT,
              f"son 7 günde {u_cur} tekil içerik (en az {config.MIN_UNIQUE_CURRENT})"),
        Check("yazar_cesitliligi", len(authors) >= config.MIN_AUTHORS_CURRENT,
              f"{len(authors)} farklı yazar (en az {config.MIN_AUTHORS_CURRENT})"),
        Check("gunlere_yayilim", len(days) >= config.MIN_ACTIVE_DAYS_CURRENT,
              f"{len(days)} farklı gün (en az {config.MIN_ACTIVE_DAYS_CURRENT})"),
        Check("tek_gune_yigilmama", max_share <= config.MAX_SINGLE_DAY_SHARE,
              f"en yoğun gün payı %{max_share*100:.0f} (en fazla %{config.MAX_SINGLE_DAY_SHARE*100:.0f})"),
        Check("kaynak_cesitliligi", len(sources) >= config.MIN_SOURCES,
              f"kaynaklar: {', '.join(sources) or '-'} (en az {config.MIN_SOURCES})"),
    ]
    checks += list(extra_checks or [])
    failed = [c for c in checks if not c.passed]

    if clean_s < config.RISE_THRESHOLD:
        status, conf = "yukselis_yok", "-"
    elif not failed:
        status = "yukselis_adayi"
        strong = u_cur >= 2 * config.MIN_UNIQUE_CURRENT and len(authors) >= 2 * config.MIN_AUTHORS_CURRENT
        conf = "yuksek" if strong else "orta"
    else:
        status, conf = "dogrulanamadi", "dusuk"

    evidence = [
        {"source": r.source, "url": r.url, "published_at": r.published_at,
         "collected_at": r.collected_at, "text": r.text[:160]}
        for r in sorted(clean_cur, key=lambda r: r.published_dt)
    ]
    seen, ev = set(), []
    by_url = {r.url: r for r in clean_cur}
    for e in evidence:
        cid = cluster[by_url[e["url"]].id]
        if cid not in seen:
            seen.add(cid); ev.append(e)
    return GroupSignal(
        group=name, raw_current=len(cur), raw_previous=len(prev),
        unique_current=u_cur, unique_previous=u_prev,
        raw_score=raw_s, clean_score=clean_s, duplicate_effect=round(raw_s - clean_s, 3),
        authors_current=len(authors), sources_current=sources,
        active_days_current=len(days), max_day_share=max_share,
        daily_current=dict(sorted(days.items())),
        status=status, confidence=conf, checks=checks,
        missing=[c.detail for c in failed] if status != "yukselis_yok" else [],
        evidence=ev[:5],
    )


DIMENSIONS: dict[str, Callable[[Record], str]] = {
    "tema": lambda r: assign_theme(r.text)[0],
    "firma": assign_carrier,
}


def analyze(records: list[Record], asof: datetime,
            bots: Optional[set[str]] = None,
            dimensions: Optional[dict[str, Callable[[Record], str]]] = None) -> dict:
    bots = bots or set()
    dimensions = dimensions or DIMENSIONS
    cluster = near_duplicate_clusters(records)
    groups: dict[str, list[Record]] = defaultdict(list)
    for dim, fn in dimensions.items():
        for r in records:
            groups[f"{dim}:{fn(r)}"].append(r)

    cov = coverage(records, asof)
    extra = [coverage_check(cov)]
    results = [analyze_group(g, rs, asof, cluster, bots, extra) for g, rs in groups.items()]
    results.append(analyze_group("TUMU", records, asof, cluster, bots, extra))
    order = {"yukselis_adayi": 0, "dogrulanamadi": 1, "yukselis_yok": 2}
    results.sort(key=lambda s: (order[s.status], -sum(c.passed for c in s.checks), -s.clean_score, s.group))

    cur, prev, undated, older = split_periods(records, asof)
    return {
        "asof": asof.isoformat(),
        "periods": {
            "current": [(asof - timedelta(days=7)).isoformat(), asof.isoformat()],
            "previous": [(asof - timedelta(days=14)).isoformat(), (asof - timedelta(days=7)).isoformat()],
        },
        "coverage": cov,
        "totals": {"records": len(records), "current": len(cur), "previous": len(prev),
                   "undated": len(undated), "outside_windows": len(older),
                   "unique_clusters": len(set(cluster.values())),
                   "bot_authors_excluded": len(bots)},
        "groups": results,
    }
