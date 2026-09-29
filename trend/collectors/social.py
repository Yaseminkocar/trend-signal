from __future__ import annotations

import os
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional
from urllib.parse import quote

from .. import config
from ..issues import log_issue
from ..privacy import mask_mentions, mask_user
from ..schema import Record, now_utc_iso
from .x import is_relevant


def _walk(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def _ts(value) -> Optional[str]:
    try:
        v = int(value)
    except (TypeError, ValueError):
        return None
    if v <= 0:
        return None
    return datetime.fromtimestamp(v, tz=timezone.utc).isoformat()


def parse_tiktok_items(data: Any, collected_at: str, query: str) -> list[Record]:
    out = []
    for d in _walk(data):
        if "createTime" not in d or "desc" not in d or "id" not in d:
            continue
        author = d.get("author") if isinstance(d.get("author"), dict) else {}
        handle = author.get("uniqueId") or (d.get("author") if isinstance(d.get("author"), str) else None)
        text = (d.get("desc") or "").strip()
        if not text:
            continue
        stats = d.get("stats") or {}
        out.append(Record(
            source="tiktok",
            url=f"https://www.tiktok.com/@/video/{d['id']}",
            text=mask_mentions(text),
            published_at=_ts(d.get("createTime")),
            collected_at=collected_at,
            author=mask_user(handle),
            query=query,
            extra={"likes": stats.get("diggCount"), "comments": stats.get("commentCount"),
                   "plays": stats.get("playCount"),
                   "author_followers": (d.get("authorStats") or {}).get("followerCount")},
        ))
    return out


def parse_instagram_items(data: Any, collected_at: str, query: str) -> list[Record]:
    out = []
    for d in _walk(data):
        if "taken_at" not in d or "code" not in d:
            continue
        cap = d.get("caption")
        text = cap.get("text") if isinstance(cap, dict) else (cap if isinstance(cap, str) else "")
        text = (text or "").strip()
        if not text:
            continue
        user = d.get("user") if isinstance(d.get("user"), dict) else {}
        out.append(Record(
            source="instagram",
            url=f"https://www.instagram.com/p/{d['code']}",
            text=mask_mentions(text),
            published_at=_ts(d.get("taken_at")),
            collected_at=collected_at,
            author=mask_user(user.get("username")),
            query=query,
            extra={"likes": d.get("like_count"), "comments": d.get("comment_count")},
        ))
    return out


def _within(rec: Record, days: int) -> bool:
    if not rec.published_at:
        return True
    return datetime.fromisoformat(rec.published_at) >= datetime.now(timezone.utc) - timedelta(days=days + 1)


def _browse(targets: list[tuple[str, str]], want: Callable[[str], bool],
            parse: Callable[[Any, str, str], list[Record]], source: str, days: int,
            cookies: list[dict], headless: bool, scrolls: int, sink) -> list[Record]:
    from playwright.sync_api import sync_playwright
    from ..fetchers import UA

    found: dict[str, Record] = {}
    stats = {"api": 0, "items": 0, "old": 0, "irrelevant": 0}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        ctx = browser.new_context(user_agent=UA, locale="tr-TR", viewport={"width": 1280, "height": 900})
        if cookies:
            ctx.add_cookies(cookies)
        page = ctx.new_page()
        responses: list = []

        def on_response(resp):
            try:
                if want(resp.url):
                    responses.append(resp)
            except Exception:
                pass

        page.on("response", on_response)
        for query, url in targets:
            responses.clear()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(6000)
            except Exception as e:
                log_issue(source, "sayfa_hatasi", f"{type(e).__name__}: {e} | {url}", "sorgu atlandi")
                continue
            if "login" in page.url:
                log_issue(source, "login_duvari", page.url[:120], "giris gerekli, sorgu atlandi")
                continue
            before = len(found)
            for _ in range(scrolls):
                page.mouse.wheel(0, 4000)
                page.wait_for_timeout(random.randint(2000, 3500))
            for resp in list(responses):
                try:
                    data = resp.json()
                except Exception:
                    continue
                stats["api"] += 1
                for rec in parse(data, now_utc_iso(), query):
                    stats["items"] += 1
                    if not _within(rec, days):
                        stats["old"] += 1
                        continue
                    if not is_relevant(rec.text):
                        stats["irrelevant"] += 1
                        continue
                    found.setdefault(rec.id, rec)
            new = [r for r in found.values() if r.query == query]
            if sink and new:
                sink(new)
            print(f"[{source}] '{query}' -> {len(found) - before} yeni kayit")
            if len(found) == before:
                log_issue(source, "bos_sorgu", url, "api yaniti yok ya da son gunlerde icerik yok")
            page.wait_for_timeout(random.randint(3000, 6000))
        browser.close()
    print(f"[{source}] {stats}")
    if stats["old"]:
        log_issue(source, "eski_icerik", f"{stats['old']} oge {days} gunden eski",
                  "arama sonucu tarihe gore degil alakaya gore siralaniyor; eski icerik elendi")
    return list(found.values())


def collect_tiktok(queries: list[str] | None = None, days: int = 14, headless: bool = True,
                   scrolls: int = 4, sink=None) -> list[Record]:
    queries = queries or config.TIKTOK_QUERIES
    targets = [(q, f"https://www.tiktok.com/search/video?q={quote(q)}") for q in queries]
    want = lambda u: "/api/search/" in u or "/api/challenge/item_list" in u
    return _browse(targets, want, parse_tiktok_items, "tiktok", days, [], headless, scrolls, sink)


def collect_instagram(tags: list[str] | None = None, days: int = 14, headless: bool = True,
                      scrolls: int = 4, sink=None) -> list[Record]:
    from dotenv import load_dotenv
    load_dotenv(config.ROOT / ".env")
    sid = os.getenv("IG_SESSIONID")
    cookies = []
    if sid:
        cookies = [{"name": "sessionid", "value": sid, "domain": ".instagram.com", "path": "/",
                    "secure": True, "httpOnly": True, "sameSite": "None"}]
    else:
        print("[instagram] IG_SESSIONID yok, girissiz deneniyor")
    tags = tags or config.INSTAGRAM_TAGS
    targets = [(t, f"https://www.instagram.com/explore/tags/{quote(t)}/") for t in tags]
    want = lambda u: ("/api/v1/" in u or "/graphql" in u) and "instagram.com" in u
    return _browse(targets, want, parse_instagram_items, "instagram", days, cookies, headless, scrolls, sink)
