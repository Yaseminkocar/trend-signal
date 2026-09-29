from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from trend.fetchers import UA

TARGETS = [
    ("tiktok", "arama", "https://www.tiktok.com/search?q=kargo%20gecikti"),
    ("tiktok", "etiket", "https://www.tiktok.com/tag/kargo"),
    ("instagram", "etiket", "https://www.instagram.com/explore/tags/kargo/"),
    ("instagram", "arama", "https://www.instagram.com/explore/search/keyword/?q=kargo"),
]


def find_items(obj, keys=("createTime", "create_time", "taken_at")) -> int:
    n = 0
    if isinstance(obj, dict):
        if any(k in obj for k in keys) and any(k in obj for k in ("desc", "caption", "id", "pk")):
            n += 1
        for v in obj.values():
            n += find_items(v, keys)
    elif isinstance(obj, list):
        for v in obj:
            n += find_items(v, keys)
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headful", action="store_true")
    a = ap.parse_args()
    from playwright.sync_api import sync_playwright

    rows = []
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=not a.headful)
        ctx = b.new_context(user_agent=UA, locale="tr-TR", viewport={"width": 1280, "height": 900})
        for platform, kind, url in TARGETS:
            page = ctx.new_page()
            api = []
            page.on("response", lambda r: api.append(r) if (
                "/api/" in r.url and "json" in (r.headers.get("content-type") or "")) else None)
            t0 = time.time()
            note = ""
            try:
                resp = page.goto(url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(6000)
                page.mouse.wheel(0, 4000)
                page.wait_for_timeout(3000)
                status = resp.status if resp else 0
            except Exception as e:
                status, note = 0, f"{type(e).__name__}: {str(e)[:80]}"
            final = page.url
            items = 0
            for r in api:
                try:
                    items += find_items(r.json())
                except Exception:
                    pass
            html = page.content().lower()
            login_wall = ("login" in final or "accounts/login" in final or "giriş yap" in html[:200000]
                          and items == 0)
            captcha = "captcha" in html or "verify" in final
            rows.append((platform, kind, url, status, final[:80], len(api), items,
                         "evet" if login_wall else "hayır", "evet" if captcha else "hayır",
                         f"{time.time() - t0:.1f}s", note))
            print(rows[-1])
            page.close()
        b.close()

    out = Path(__file__).parent / "social_probe.md"
    L = [f"# TikTok / Instagram denemesi ({time.strftime('%Y-%m-%d %H:%M')}, giriş yapılmadan)", "",
         "| Platform | Tür | HTTP | Son URL | API yanıtı | Tarihli öğe | Login duvarı | Captcha | Süre | Not |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    L += [f"| {r[0]} | {r[1]} | {r[3]} | {r[4]} | {r[5]} | {r[6]} | {r[7]} | {r[8]} | {r[9]} | {r[10]} |" for r in rows]
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
