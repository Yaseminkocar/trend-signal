from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime

from . import config, issues, store
from .profiles import AccountProfile


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
                                  discover=not a.no_discover, save_html_dir=dbg, today=a.until):
                batch.append(r)
                if len(batch) >= 50:
                    added_total += store.upsert(config.RAW_PATH, batch)[0]; batch = []
        finally:
            added_total += store.upsert(config.RAW_PATH, batch)[0]
            f.close()
        print(f"[eksi] yeni kayıt: {added_total}")
    elif a.source in ("tiktok", "instagram"):
        _collect_social(a)
    elif a.source == "x":
        from .collectors import x
        skip = frozenset()
        if a.fill_gaps:
            from collections import Counter
            have = Counter((r.query, r.published_dt.astimezone(config.TR_TZ).date().isoformat())
                           for r in store.load(config.RAW_PATH) if r.source == "x" and r.published_at)
            skip = frozenset(k for k, n in have.items() if n >= min(a.per_day, 15))
            print(f"[x] --fill-gaps: {len(skip)} (sorgu, gün) çifti zaten dolu, atlanacak")
        print(f"[x] konu: {config.TOPIC}, sorgular: {'; '.join(config.X_QUERIES)}")
        recs, profiles = x.collect(days=a.days, per_day=a.per_day, with_profiles=a.profiles, skip=skip, today=a.until,
                                   sink=lambda rs: store.upsert(config.RAW_PATH, rs),
                                   backend=a.x_backend, headless=not a.headful,
                                   debug_dir=_debug_dir(a), retry=not a.no_retry)
        added, dup = store.upsert(config.RAW_PATH, recs)
        _upsert_profiles(profiles)
        print(f"[x] {len(recs)} tweet ({added} yeni, {dup} zaten vardı), {len(profiles)} profil")


def _debug_dir(a):
    if not a.save_html:
        return None
    d = config.DATA_DIR / "debug"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _collect_social(a) -> None:
    from .collectors import social
    sink = lambda rs: store.upsert(config.RAW_PATH, rs)
    until = None
    if a.until:
        until = datetime.combine(a.until, datetime.max.time(), tzinfo=config.TR_TZ)
    if a.source == "tiktok":
        recs = social.collect_tiktok(days=a.days, headless=not a.headful, sink=sink, until=until)
    else:
        recs = social.collect_instagram(days=a.days, headless=not a.headful, sink=sink, until=until)
    added, dup = store.upsert(config.RAW_PATH, recs)
    print(f"[{a.source}] {len(recs)} kayit ({added} yeni, {dup} zaten vardi)")


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


def cmd_analyze(a) -> None:
    from .pipeline import Options, run_analysis
    from .report import write
    opts = Options(sources=tuple(a.sources.split(",")) if a.sources else (),
                   asof=datetime.fromisoformat(a.asof) if a.asof else None, window=a.window)
    out = run_analysis(opts)
    warn = [n for n in out.notes if n.startswith("uyari")]
    for n in out.notes:
        if n not in warn:
            print(n)
    result = out.result
    md = write(result, out.verdicts, config.OUTPUT_DIR)
    t = result["totals"]
    w = result["window_days"]
    print(f"\nanaliz: {result['asof']}")
    print(f"kayit: {t['records']}  son {w} gun: {t['current']}  onceki {w} gun: {t['previous']}")
    print(f"{'grup':32} {'onceki':>7} {'son':>5} {'puan':>6}  durum")
    for g in result["groups"]:
        if g.status == "yukselis_yok" and g.group != "TUMU":
            continue
        print(f"{g.group:32} {g.unique_previous:>7} {g.unique_current:>5} {g.clean_score:>+6.2f}  {g.status}")
        if g.missing:
            print(f"{'':32} eksik: {'; '.join(g.missing)}")
    for n in warn:
        print(f"\n{n}. topics/{config.TOPIC}.json dosyasina baslik/sorgu ekleyin ya da ikinci kaynak toplayin")
    print(f"\ndetayli rapor: {md.relative_to(config.ROOT)}")


def cmd_stats(a) -> None:
    rs = store.load(config.RAW_PATH)
    print(f"toplam: {len(rs)}")
    print("kaynak:", dict(Counter(r.source for r in rs)))
    print("yayın zamanı yok:", sum(r.published_at is None for r in rs))
    days = Counter((r.source, r.published_at[:10]) for r in rs if r.published_at)
    for (s, d), n in sorted(days.items()):
        print(f"  {s:5} {d} {'#' * min(n, 60)} {n}")
    print("sorunlar:", dict(issues.summarize()))


def cmd_topics(a) -> None:
    for name in config.available_topics():
        mark = "*" if name == config.TOPIC else " "
        print(f"{mark} {name}")


def cmd_init_topic(a) -> None:
    from .topics import init_topic
    path = init_topic(a.name, a.label or a.name, a.keywords.split(","), (a.brands or "").split(","), a.force)
    print(f"olusturuldu: {path.relative_to(config.ROOT)}")
    print("sorgulari ve tema sozlugunu kontrol edip gerekirse duzenleyin, sonra:")
    print(f"  python -m trend --topic {a.name} collect eksi")


def cmd_run(a) -> None:
    from .topics import _slug, init_topic, keywords_from_label
    name = a.name or _slug(a.label).replace("-", "_")
    if name not in config.available_topics():
        keywords = a.keywords.split(",") if a.keywords else keywords_from_label(a.label)
        init_topic(name, a.label, keywords, (a.brands or "").split(","))
        print(f"yeni konu: topics/{name}.json")
    else:
        print(f"mevcut konu kullaniliyor: topics/{name}.json")
    days = a.days or 2 * a.window
    sources = []
    for src in [s.strip() for s in a.collect.split(",") if s.strip()]:
        print(f"\n== {src} ==")
        try:
            main(["--topic", name, "collect", src, "--days", str(days)])
            sources.append(src)
        except SystemExit as e:
            print(f"{src} atlandi: {e}")
        except Exception as e:
            print(f"{src} atlandi: {type(e).__name__}: {e}")
    if not sources:
        raise SystemExit("hicbir kaynaktan veri toplanamadi")
    if len(sources) < config.MIN_SOURCES:
        print(f"\nuyari: yalniz {', '.join(sources)} ile analiz ediliyor; tek kaynakla sonuc en fazla 'dogrulanamadi' olabilir")
    args = ["--topic", name, "analyze", "--sources", ",".join(sources), "--window", str(a.window)]
    if a.asof:
        args += ["--asof", a.asof]
    main(args)
    print(f"\nsonuclari iyilestirmek icin topics/{name}.json dosyasindaki sorgu ve temalari gozden gecirip tekrar calistirin")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="trend")
    p.add_argument("--topic", default=None, help="topics/<ad>.json (varsayilan: kargo)")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect"); c.add_argument("source", choices=["eksi", "x", "tiktok", "instagram"])
    c.add_argument("--backend", default="scrapling", choices=["requests", "scrapling", "playwright"])
    c.add_argument("--days", type=int, default=config.EKSI_DAYS)
    c.add_argument("--until", type=lambda v: datetime.strptime(v, "%Y-%m-%d").date(), default=None,
                   help="toplama penceresinin son gunu (YYYY-MM-DD); varsayilan bugun")
    c.add_argument("--per-day", type=int, default=config.X_TWEETS_PER_DAY)
    c.add_argument("--profiles", type=int, default=30)
    c.add_argument("--delay", type=float, default=1.5)
    c.add_argument("--topics", nargs="*", default=None)
    c.add_argument("--x-backend", default="playwright", choices=["playwright", "twikit"])
    c.add_argument("--fill-gaps", action="store_true", help="X: zaten dolu (sorgu, gün) çiftlerini atla")
    c.add_argument("--no-retry", action="store_true", help="X: bos gunde 60-90 s bekleyip tekrar deneme")
    c.add_argument("--headful", action="store_true", help="X için tarayıcı penceresini göster")
    c.add_argument("--no-discover", action="store_true", help="Ekşi aramasıyla başlık keşfini kapat")
    c.add_argument("--save-html", action="store_true", help="hata ayıklama için ham HTML'i data/debug/ altına kaydet")
    c.set_defaults(fn=cmd_collect)
    an = sub.add_parser("analyze"); an.add_argument("--asof", default=None)
    an.add_argument("--window", type=int, default=7, help="kiyas donemi (gun): son N gun ile onceki N gun")
    an.add_argument("--sources", default=None); an.set_defaults(fn=cmd_analyze)
    st = sub.add_parser("stats"); st.set_defaults(fn=cmd_stats)
    tp = sub.add_parser("topics"); tp.set_defaults(fn=cmd_topics)
    rn = sub.add_parser("run", help="konu olustur (yoksa) + topla + analiz et")
    rn.add_argument("label", help='ornek: "elektrikli scooter"')
    rn.add_argument("--name", default=None)
    rn.add_argument("--keywords", default=None, help="virgulle; verilmezse konu adi kullanilir")
    rn.add_argument("--brands", default="")
    rn.add_argument("--collect", default="eksi,x", help="virgulle: eksi,x,tiktok,instagram")
    rn.add_argument("--days", type=int, default=None, help="varsayilan: 2 x --window")
    rn.add_argument("--asof", default=None)
    rn.add_argument("--window", type=int, default=7)
    rn.set_defaults(fn=cmd_run)
    it = sub.add_parser("init-topic"); it.add_argument("name")
    it.add_argument("--label", default=None)
    it.add_argument("--keywords", required=True, help="virgulle: elektrikli arac,sarj istasyonu")
    it.add_argument("--brands", default="", help="virgulle: togg,tesla,byd")
    it.add_argument("--force", action="store_true")
    it.set_defaults(fn=cmd_init_topic)
    a = p.parse_args(argv)
    if a.topic:
        config.use_topic(a.topic)
    a.fn(a)
