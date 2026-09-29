from __future__ import annotations

import argparse
import asyncio
import platform
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trend.collectors.eksi import parse_topic_page
from trend.fetchers import HEADERS, UA, _looks_like_challenge

DEFAULT_URL = "https://eksisozluk.com/?q=yurti%C3%A7i+kargo"


def via_requests(url):
    import requests
    r = requests.get(url, headers=HEADERS, timeout=20)
    return r.status_code, r.url, r.text


def via_scrapling(url):
    from scrapling.fetchers import Fetcher
    p = Fetcher.get(url, stealthy_headers=True, follow_redirects=True, timeout=20, retries=1)
    return int(p.status), str(p.url), str(p.html_content)


def via_playwright(url):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_context(user_agent=UA, locale="tr-TR").new_page()
        resp = pg.goto(url, wait_until="domcontentloaded", timeout=30000)
        html, final = pg.content(), pg.url
        b.close()
        return (resp.status if resp else 0), final, html


def via_crawl4ai(url):
    from crawl4ai import AsyncWebCrawler

    async def run():
        async with AsyncWebCrawler() as c:
            r = await c.arun(url=url)
            return (r.status_code or 0), (r.redirected_url or url), (r.html or "")
    return asyncio.run(run())


TOOLS = {"requests+bs4": via_requests, "scrapling": via_scrapling,
         "playwright": via_playwright, "crawl4ai": via_crawl4ai}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--tools", nargs="*", default=list(TOOLS))
    a = ap.parse_args()

    rows = []
    for name in a.tools:
        times, status, n, dated, err, final = [], None, 0, 0, "", ""
        for _ in range(a.runs):
            t0 = time.time()
            try:
                status, final, html = TOOLS[name](a.url)
                times.append(time.time() - t0)
                if _looks_like_challenge(html):
                    err = "Cloudflare/JS challenge sayfası döndü"
                recs, _, _ = parse_topic_page(html, final, "2026-01-01T00:00:00+00:00", "bench")
                n, dated = len(recs), sum(r.published_at is not None for r in recs)
            except ImportError as e:
                err = f"kurulu değil: {e}"; break
            except Exception as e:
                err = f"{type(e).__name__}: {str(e)[:120]}"
                traceback.print_exc(limit=1)
            time.sleep(2)
        avg = f"{sum(times) / len(times):.2f}s" if times else "-"
        rows.append((name, status, n, dated, avg, err or "ok"))
        print(rows[-1])

    out = Path(__file__).parent / "results.md"
    lines = [f"# Araç karşılaştırması ({time.strftime('%Y-%m-%d %H:%M')}, {platform.system()}, Python {platform.python_version()})",
             "", f"URL: {a.url} - {a.runs} deneme", "",
             "| Araç | HTTP | Entry | Tarihli | Ort. süre | Not |", "|---|---|---|---|---|---|"]
    lines += [f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |" for r in rows]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
