from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from . import config, store
from .profiles import AccountProfile, BotVerdict, score_profile


@dataclass
class Options:
    sources: tuple[str, ...] = ()
    asof: Optional[datetime] = None
    window: int = 7
    relevance_filter: bool = True
    ad_filter: bool = True
    bot_filter: bool = True
    min_sources: Optional[int] = None


@dataclass
class Outcome:
    result: dict
    verdicts: list[BotVerdict]
    notes: list[str] = field(default_factory=list)
    records: list = field(default_factory=list)


def load_profiles() -> list[AccountProfile]:
    if not config.PROFILES_PATH.exists():
        return []
    return [AccountProfile.from_dict(json.loads(l))
            for l in config.PROFILES_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]


def run_analysis(opts: Options) -> Outcome:
    from .analysis.ads import is_ad
    from .analysis.signal import analyze, balance_sampled, drop_unbalanced_queries
    from .collectors.x import is_relevant

    notes: list[str] = []
    records = store.load(config.RAW_PATH)
    sources = tuple(opts.sources) or config.SIGNAL_SOURCES
    skipped = sum(r.source not in sources for r in records)
    records = [r for r in records if r.source in sources]
    if skipped:
        notes.append(f"kaynaklar: {', '.join(sources)} ({skipped} kayit diger kaynaklardan, analize alinmadi)")
    if not records:
        raise SystemExit(f"{config.RAW_PATH} icinde secilen kaynaklardan kayit yok. Once veri toplayin.")

    if opts.relevance_filter:
        before = len(records)
        records = [r for r in records if r.source == "eksi" or is_relevant(r.text)]
        if before != len(records):
            notes.append(f"konu ile ilgisiz {before - len(records)} kayit cikarildi")

    ads: Counter = Counter()
    if opts.ad_filter:
        ads = Counter(r.source for r in records if r.source in config.AD_FILTER_SOURCES and is_ad(r.text)[0])
        records = [r for r in records if not (r.source in config.AD_FILTER_SOURCES and is_ad(r.text)[0])]
        for src, n in ads.items():
            notes.append(f"{src}: {n} ilan/kurumsal gonderi cikarildi")

    asof = opts.asof or datetime.now(config.TR_TZ).replace(microsecond=0)
    verdicts = [score_profile(p, asof) for p in load_profiles()]
    bots = {v.author for v in verdicts if v.label == "bot_olasi"} if opts.bot_filter else set()

    records, dropped = balance_sampled(records, config.X_TWEETS_PER_DAY)
    if dropped:
        notes.append(f"gunluk ust sinir ({config.X_TWEETS_PER_DAY}) asildigi icin {dropped} kayit cikarildi")
    records, excluded = drop_unbalanced_queries(records, asof, opts.window)
    for q, why in excluded.items():
        notes.append(f"sorgu disarida birakildi ({why}): {q}")

    result = analyze(records, asof, bots=bots, window=opts.window, min_sources=opts.min_sources)
    result["excluded_queries"] = excluded
    result["ads_excluded"] = dict(ads)
    t = result["totals"]
    if t["current"] + t["previous"] < 2 * config.MIN_UNIQUE_CURRENT:
        notes.append(f"uyari: iki donemde toplam {t['current'] + t['previous']} kayit var; sonuc icin veri cok az")
    return Outcome(result, verdicts, notes, records)
