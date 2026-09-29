from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime

from . import config, issues, store
from .profiles import AccountProfile, score_profile


def cmd_collect(a) -> None:
    if a.source == "eksi":
        from .collectors import eksi
        from .fetchers import make_fetcher
        f = make_fetcher(a.backend, delay=a.delay)
        batch, added_total = [], 0
        try:
            dbg = config.DATA_DIR / "debug" if a.save_html else None
            if dbg:
                dbg.mkdir(parents=True, exist_ok=True)
            for r in eksi.collect(f, topics=a.topics, days=a.days, max_pages=config.EKSI_MAX_PAGES_PER_TOPIC,
                                  discover=not a.no_discover, save_html_dir=dbg):
                batch.append(r)
                if len(batch) >= 50:
                    added_total += store.upsert(config.RAW_PATH, batch)[0]; batch = []
        finally:
            added_total += store.upsert(config.RAW_PATH, batch)[0]
            f.close()
        print(f"[eksi] yeni kayıt: {added_total}")
    elif a.source == "x":
        from .collectors import x
        skip = frozenset()
        if a.fill_gaps:
            from collections import Counter
            have = Counter((r.query, r.published_dt.astimezone(config.TR_TZ).date().isoformat())
                           for r in store.load(config.RAW_PATH) if r.source == "x" and r.published_at)
            skip = frozenset(k for k, n in have.items() if n >= min(a.per_day, 15))
            print(f"[x] --fill-gaps: {len(skip)} (sorgu, gün) çifti zaten dolu, atlanacak")
        recs, profiles = x.collect(days=a.days, per_day=a.per_day, with_profiles=a.profiles, skip=skip,
                                   sink=lambda rs: store.upsert(config.RAW_PATH, rs),
                                   backend=a.x_backend, headless=not a.headful,
                                   debug_dir=_debug_dir(a))
        added, dup = store.upsert(config.RAW_PATH, recs)
        _upsert_profiles(profiles)
        print(f"[x] {len(recs)} tweet ({added} yeni, {dup} zaten vardı), {len(profiles)} profil")


def _debug_dir(a):
    if not a.save_html:
        return None
    d = config.DATA_DIR / "debug"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _upsert_profiles(profiles: list[AccountProfile]) -> None:
    path = config.PROFILES_PATH
    existing = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                p = AccountProfile.from_dict(json.loads(line)); existing[(p.source, p.author)] = p
    for p in profiles:
        existing[(p.source, p.author)] = p
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(p.to_dict(), ensure_ascii=False) + "\n"
                            for p in sorted(existing.values(), key=lambda p: p.author)), encoding="utf-8")


def load_profiles() -> list[AccountProfile]:
    if not config.PROFILES_PATH.exists():
        return []
    return [AccountProfile.from_dict(json.loads(l))
            for l in config.PROFILES_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]


def cmd_analyze(a) -> None:
    from .analysis.signal import analyze
    from .report import write
    records = store.load(config.RAW_PATH)
    if not records:
        raise SystemExit(f"{config.RAW_PATH} boş. Önce 'python -m trend collect ...' çalıştırın.")
    from .collectors.x import is_relevant
    before = len(records)
    records = [r for r in records if r.source != "x" or is_relevant(r.text)]
    if before != len(records):
        print(f"[analyze] metninde kargo bağlamı olmayan {before - len(records)} X kaydı analiz dışı bırakıldı")
    asof = datetime.fromisoformat(a.asof) if a.asof else datetime.now(config.TR_TZ).replace(microsecond=0)
    verdicts = [score_profile(p, asof) for p in load_profiles()]
    bots = {v.author for v in verdicts if v.label == "bot_olasi"}
    from .analysis.signal import balance_sampled
    records, dropped = balance_sampled(records, config.X_TWEETS_PER_DAY)
    if dropped:
        print(f"[analyze] X örneklem dengesi: (sorgu, gün) başına en fazla {config.X_TWEETS_PER_DAY}; {dropped} fazla kayıt analiz dışı")
    from .analysis.signal import drop_unbalanced_queries
    records, excluded = drop_unbalanced_queries(records, asof)
    for q, why in excluded.items():
        print(f"[analyze] dengesiz kapsamalı sorgu analiz dışı: {q} ({why})")
    result = analyze(records, asof, bots=bots)
    result["excluded_queries"] = excluded
    md = write(result, verdicts, config.OUTPUT_DIR)
    print(md.read_text(encoding="utf-8"))


def cmd_stats(a) -> None:
    rs = store.load(config.RAW_PATH)
    print(f"toplam: {len(rs)}")
    print("kaynak:", dict(Counter(r.source for r in rs)))
    print("yayın zamanı yok:", sum(r.published_at is None for r in rs))
    days = Counter((r.source, r.published_at[:10]) for r in rs if r.published_at)
    for (s, d), n in sorted(days.items()):
        print(f"  {s:5} {d} {'#' * min(n, 60)} {n}")
    print("sorunlar:", dict(issues.summarize()))


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="trend")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect"); c.add_argument("source", choices=["eksi", "x"])
    c.add_argument("--backend", default="scrapling", choices=["requests", "scrapling", "playwright"])
    c.add_argument("--days", type=int, default=config.EKSI_DAYS)
    c.add_argument("--per-day", type=int, default=config.X_TWEETS_PER_DAY)
    c.add_argument("--profiles", type=int, default=30)
    c.add_argument("--delay", type=float, default=1.5)
    c.add_argument("--topics", nargs="*", default=None)
    c.add_argument("--x-backend", default="playwright", choices=["playwright", "twikit"])
    c.add_argument("--fill-gaps", action="store_true", help="X: zaten dolu (sorgu, gün) çiftlerini atla")
    c.add_argument("--headful", action="store_true", help="X için tarayıcı penceresini göster")
    c.add_argument("--no-discover", action="store_true", help="Ekşi aramasıyla başlık keşfini kapat")
    c.add_argument("--save-html", action="store_true", help="hata ayıklama için ham HTML'i data/debug/ altına kaydet")
    c.set_defaults(fn=cmd_collect)
    an = sub.add_parser("analyze"); an.add_argument("--asof", default=None); an.set_defaults(fn=cmd_analyze)
    st = sub.add_parser("stats"); st.set_defaults(fn=cmd_stats)
    a = p.parse_args(argv)
    a.fn(a)
