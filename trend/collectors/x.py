from __future__ import annotations

import asyncio
import os
import random
import time
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any, Iterator, Optional

from .. import config
from ..issues import log_issue
from ..privacy import mask_mentions, mask_user
from ..profiles import AccountProfile, handle_has_digit_suffix
from ..schema import Record, now_utc_iso

SOURCE = "x"


def parse_x_date(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%a %b %d %H:%M:%S %z %Y").isoformat()
    except ValueError:
        try:
            return parsedate_to_datetime(s).isoformat()
        except (TypeError, ValueError):
            return None


def _unwrap(result: dict) -> dict:
    return result.get("tweet", result) if result.get("__typename") != "Tweet" else result


def _user_fields(user_result: dict) -> dict:
    legacy = user_result.get("legacy", {}) or {}
    core = user_result.get("core", {}) or {}
    avatar = user_result.get("avatar", {}) or {}
    return {
        "id": user_result.get("rest_id"),
        "screen_name": core.get("screen_name") or legacy.get("screen_name"),
        "created_at": core.get("created_at") or legacy.get("created_at"),
        "followers": (user_result.get("relationship_counts") or {}).get("followers", legacy.get("followers_count")),
        "following": (user_result.get("relationship_counts") or {}).get("following", legacy.get("friends_count")),
        "statuses": (user_result.get("tweet_counts") or {}).get("tweets", legacy.get("statuses_count")),
        "default_image": legacy.get("default_profile_image",
                                    "default_profile_images" in (avatar.get("image_url") or "")),
        "verified": bool(user_result.get("is_blue_verified") or legacy.get("verified")
                         or (user_result.get("verification") or {}).get("verified")),
    }


def parse_tweet_result(result: dict, collected_at: str, query: str) -> Optional[tuple[Record, dict]]:
    t = _unwrap(result)
    legacy = t.get("legacy") or {}
    if not legacy or legacy.get("retweeted_status_result"):
        return None
    user = _user_fields(t.get("core", {}).get("user_results", {}).get("result", {}) or {})
    tweet_id = legacy.get("id_str") or t.get("rest_id")
    if not tweet_id:
        return None
    note = (t.get("note_tweet", {}) or {}).get("note_tweet_results", {}).get("result", {}).get("text")
    text = note or legacy.get("full_text", "")
    rec = Record(
        source=SOURCE,
        url=f"https://x.com/i/status/{tweet_id}",
        text=mask_mentions(text),
        published_at=parse_x_date(legacy.get("created_at")),
        collected_at=collected_at,
        author=mask_user(user.get("screen_name")),
        query=query,
        extra={"lang": legacy.get("lang"), "likes": legacy.get("favorite_count"),
               "retweets": legacy.get("retweet_count"), "replies": legacy.get("reply_count"),
               "is_reply": bool(legacy.get("in_reply_to_status_id_str")),
               "is_quote": bool(legacy.get("is_quote_status"))},
    )
    return rec, user


def build_profile(user: dict, recent: list[Record], collected_at: str) -> AccountProfile:
    return AccountProfile(
        author=mask_user(user.get("screen_name")) or "?",
        source=SOURCE,
        collected_at=collected_at,
        created_at=parse_x_date(user.get("created_at")),
        followers=user.get("followers"), following=user.get("following"),
        statuses=user.get("statuses"), default_image=user.get("default_image"),
        verified=user.get("verified"),
        handle_digit_suffix=handle_has_digit_suffix(user.get("screen_name") or ""),
        recent_texts=[r.text for r in recent],
        recent_times=[r.published_at for r in recent if r.published_at],
    )


def day_queries(base_query: str, days: int, today: date) -> list[tuple[str, str]]:
    out = []
    for i in range(days + 1):
        d = today - timedelta(days=i)
        out.append((d.isoformat(), f"{base_query} since:{d.isoformat()} until:{(d + timedelta(days=1)).isoformat()}"))
    return out


def _cookies() -> dict[str, str]:
    from dotenv import load_dotenv
    load_dotenv(config.ROOT / ".env")
    auth, ct0 = os.getenv("X_AUTH_TOKEN"), os.getenv("X_CT0")
    if not auth or not ct0:
        raise SystemExit(".env içinde X_AUTH_TOKEN ve X_CT0 tanımlı olmalı (bkz. .env.example)")
    return {"auth_token": auth, "ct0": ct0}


async def _twikit_collect(queries, days, per_day, today, with_profiles):
    from twikit import Client
    from twikit.errors import TooManyRequests

    client = Client("tr-TR")
    client.set_cookies(_cookies())
    records: list[Record] = []
    users: dict[str, dict] = {}

    async def pause():
        await asyncio.sleep(random.uniform(2.5, 5.0))

    for base in queries:
        for day, q in day_queries(base, days, today):
            got = 0
            try:
                page = await client.search_tweet(q, "Latest", count=20)
                while page and got < per_day:
                    for tw in page:
                        parsed = parse_tweet_result(tw._data, now_utc_iso(), base)
                        if parsed:
                            rec, user = parsed
                            records.append(rec); users[rec.author] = user
                            got += 1
                    if got >= per_day or len(page) == 0:
                        break
                    await pause()
                    page = await page.next()
            except TooManyRequests as e:
                reset = getattr(e, "rate_limit_reset", None)
                wait = max(int(reset - time.time()), 60) if reset else 900
                log_issue(SOURCE, "rate_limit", f"{q}", f"{wait}s beklendi, sonra devam")
                await asyncio.sleep(min(wait, 900))
            except Exception as e:
                log_issue(SOURCE, "arama_hatasi", f"{type(e).__name__}: {e} | {q}", "gün atlandı")
            print(f"[x] {day} '{base[:40]}' -> {got} tweet" + (" (DOYGUN)" if got >= per_day else ""))
            if got >= per_day:
                log_issue(SOURCE, "doygun_gun", f"{day} {base}", f"üst sınır {per_day}; hacim alt sınırdır")
            await pause()

    profiles: list[AccountProfile] = []
    if with_profiles:
        for author, user in list(users.items())[:with_profiles]:
            recent: list[Record] = []
            try:
                tl = await client.get_user_tweets(user["id"], "Tweets", count=config.X_PROFILE_HISTORY)
                for tw in tl:
                    p = parse_tweet_result(tw._data, now_utc_iso(), "profile")
                    if p:
                        recent.append(p[0])
            except Exception as e:
                log_issue(SOURCE, "profil_hatasi", f"{type(e).__name__}: {e} | {author}",
                          "sadece arama sonucundaki profil alanları kullanıldı")
            profiles.append(build_profile(user, recent, now_utc_iso()))
            await pause()
    return records, profiles


def extract_tweet_results(obj: Any) -> list[dict]:
    out: list[dict] = []
    if isinstance(obj, dict):
        tr = obj.get("tweet_results")
        if isinstance(tr, dict) and isinstance(tr.get("result"), dict):
            out.append(tr["result"])
        for v in obj.values():
            if isinstance(v, (dict, list)):
                out.extend(extract_tweet_results(v))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(extract_tweet_results(v))
    return out


_RELEVANT = None


def is_relevant(text: str) -> bool:
    global _RELEVANT
    if _RELEVANT is None:
        import re
        from ..schema import normalize_text as n
        words = ["kargo", "kurye", "teslimat"] + [k for kws in config.CARRIERS.values() for k in kws]
        _RELEVANT = re.compile("|".join(re.escape(n(w)) for w in words if n(w)))
    from ..schema import normalize_text
    return bool(_RELEVANT.search(normalize_text(text)))


def response_query(url: str, post_data: Optional[str] = None) -> Optional[str]:
    import json as _json
    from urllib.parse import parse_qs, urlsplit
    try:
        v = parse_qs(urlsplit(url).query).get("variables", [None])[0]
        if v:
            return _json.loads(v).get("rawQuery")
        if post_data:
            return (_json.loads(post_data).get("variables") or {}).get("rawQuery")
    except Exception:
        return None
    return None


def graphql_op(url: str) -> Optional[str]:
    if "/graphql/" not in url:
        return None
    parts = url.split("?")[0].split("/graphql/", 1)[1].split("/")
    return parts[1] if len(parts) > 1 and parts[1] else None


def in_day(rec: Record, day: str) -> bool:
    return bool(rec.published_at) and datetime.fromisoformat(rec.published_at).astimezone(
        config.TR_TZ).date().isoformat() == day


def _pw_collect(queries, days, per_day, today, with_profiles, headless=True, debug_dir=None, skip=frozenset(), sink=None):
    import json as _json
    from urllib.parse import quote
    from playwright.sync_api import sync_playwright
    from ..fetchers import UA

    records: dict[str, Record] = {}
    users: dict[str, dict] = {}
    profiles: list[AccountProfile] = []
    responses: list = []

    dumped = [0]
    stats = {"stale_query": 0, "query_unknown": 0, "off_day": 0, "irrelevant": 0}
    seen_ops: set[str] = set()

    def on_response(resp):
        try:
            op = graphql_op(resp.url)
            if not op:
                return
            seen_ops.add(op)
            if op in ("SearchTimeline", "UserByScreenName") or "Tweets" in op or "Timeline" in op:
                responses.append(resp)
        except Exception:
            pass

    def drain(query_label: str, expect_query: Optional[str] = None) -> list[tuple[Record, dict]]:
        got = []
        while responses:
            resp = responses.pop(0)
            if expect_query and "SearchTimeline" in resp.url:
                try:
                    body = resp.request.post_data
                except Exception:
                    body = None
                rq = response_query(resp.url, body)
                if rq is None:
                    stats["query_unknown"] += 1
                elif rq != expect_query:
                    stats["stale_query"] += 1
                    continue
            try:
                data = resp.json()
            except Exception:
                continue
            if debug_dir and dumped[0] < 20:
                op = graphql_op(resp.url) or "unknown"
                try:
                    body = resp.request.post_data
                except Exception:
                    body = None
                (debug_dir / f"x_{dumped[0]:02d}_{op}.json").write_text(
                    _json.dumps({"_url": resp.url[:3000], "_method": resp.request.method, "_body": (body or "")[:3000],
                                 **data}, ensure_ascii=False, indent=1)[:2_000_000], encoding="utf-8")
                dumped[0] += 1
            if "UserByScreenName" in resp.url:
                ur = ((data.get("data") or {}).get("user") or {}).get("result") or {}
                if ur:
                    got.append((None, _user_fields(ur)))
                continue
            for res in extract_tweet_results(data):
                p = parse_tweet_result(res, now_utc_iso(), query_label)
                if p:
                    got.append(p)
        return got

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        ctx = browser.new_context(user_agent=UA, locale="tr-TR", viewport={"width": 1280, "height": 900})
        ctx.add_cookies([{"name": k, "value": v, "domain": ".x.com", "path": "/", "secure": True,
                          "httpOnly": k == "auth_token", "sameSite": "None"} for k, v in _cookies().items()])
        page = ctx.new_page()
        page.on("response", on_response)

        def search_day(base: str, day: str, q: str) -> int:
            responses.clear()
            page.goto(f"https://x.com/search?q={quote(q)}&src=typed_query&f=live",
                      wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(4000)
            if "/login" in page.url or "flow/login" in page.url:
                raise SystemExit("X giriş sayfasına yönlendirdi: cookie'ler geçersiz/süresi dolmuş.")
            seen_day: set[str] = set()
            stale = 0
            while len(seen_day) < per_day and stale < 3:
                before = len(seen_day)
                for rec, user in drain(base, expect_query=q):
                    if rec is None:
                        continue
                    if not in_day(rec, day):
                        stats["off_day"] += 1; continue
                    if not is_relevant(rec.text):
                        stats["irrelevant"] += 1; continue
                    if rec.id not in seen_day and len(seen_day) < per_day:
                        seen_day.add(rec.id)
                        records.setdefault(rec.id, rec)
                        if user.get("screen_name"):
                            users[user["screen_name"]] = user
                stale = stale + 1 if len(seen_day) == before else 0
                if len(seen_day) >= per_day:
                    break
                page.mouse.wheel(0, 4000)
                page.wait_for_timeout(random.randint(2000, 3500))
            if sink and seen_day:
                sink([records[i] for i in seen_day])
            return len(seen_day)

        for base in queries:
            for day, q in day_queries(base, days, today):
                if (base, day) in skip:
                    print(f"[x] {day} '{base[:40]}' -> zaten dolu, atlandı")
                    continue
                n = search_day(base, day, q)
                if n == 0:
                    wait = random.randint(60, 90)
                    print(f"[x] {day} boş döndü -> {wait}s bekleyip tekrar deneniyor")
                    page.wait_for_timeout(wait * 1000)
                    n = search_day(base, day, q)
                print(f"[x] {day} '{base[:40]}' -> {n} tweet" + (" (DOYGUN)" if n >= per_day else ""))
                if n >= per_day:
                    log_issue(SOURCE, "doygun_gun", f"{day} {base}", f"üst sınır {per_day}; hacim alt sınırdır")
                elif n == 0:
                    log_issue(SOURCE, "bos_gun", f"{day} {base}",
                              "bekleyip tekrar denendi, yine boş (rate limit ya da sonuç yok)")
                page.wait_for_timeout(random.randint(4000, 7000))

        for sn, user in list(users.items())[:with_profiles]:
            responses.clear()
            recent: list[Record] = []
            seen_ops.clear()
            try:
                page.goto(f"https://x.com/{sn}", wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(5000)
                for _ in range(2):
                    page.mouse.wheel(0, 3000)
                    page.wait_for_timeout(2500)
                for rec, u in drain("profile"):
                    if rec is None:
                        user = {**user, **{k: v for k, v in u.items() if v is not None}}
                    elif u.get("screen_name") == sn and len(recent) < config.X_PROFILE_HISTORY:
                        recent.append(rec)
            except Exception as e:
                log_issue(SOURCE, "profil_hatasi", f"{type(e).__name__}: {e} | {mask_user(sn)}",
                          "sadece arama sonucundaki profil alanları kullanıldı")
            if not recent:
                log_issue(SOURCE, "profil_bos", f"{mask_user(sn)} | görülen GraphQL işlemleri: {sorted(seen_ops)}",
                          "önceki paylaşımlar alınamadı")
            profiles.append(build_profile(user, recent, now_utc_iso()))
            print(f"[x] profil {mask_user(sn)}: {len(recent)} önceki tweet")
            page.wait_for_timeout(random.randint(1500, 3000))
        browser.close()
    for k, v in stats.items():
        if v:
            log_issue(SOURCE, k, f"{v} tweet/yanıt", {"stale_query": "önceki sorgunun geç yanıtı, atlandı",
                                                       "off_day": "istenen gün dışında, o günün kotasına sayılmadı",
                                                       "irrelevant": "metinde kargo bağlamı yok, elendi",
                "query_unknown": "yanıtın sorgusu okunamadı; tarih filtresiyle korundu"}[k])
    print(f"[x] filtre: {stats}")
    return list(records.values()), profiles


def collect(queries: list[str] | None = None, days: int = 14, per_day: int = 20,
            today: date | None = None, with_profiles: int = 30, backend: str = "playwright",
            headless: bool = True, debug_dir=None, skip=frozenset(), sink=None) -> tuple[list[Record], list[AccountProfile]]:
    queries = queries or config.X_QUERIES
    today = today or datetime.now(config.TR_TZ).date()
    if backend == "twikit":
        return asyncio.run(_twikit_collect(queries, days, per_day, today, with_profiles))
    return _pw_collect(queries, days, per_day, today, with_profiles, headless=headless, debug_dir=debug_dir,
                       skip=skip, sink=sink)
