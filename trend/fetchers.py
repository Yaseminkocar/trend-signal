from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Optional

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.7,en;q=0.6",
}


@dataclass
class FetchResult:
    url: str
    status: int
    html: str
    elapsed: float


class BlockedError(RuntimeError):
    pass


class Fetcher:
    name = "base"

    def __init__(self, delay: float = 1.5):
        self.delay = delay
        self._last = 0.0

    def _polite_wait(self) -> None:
        wait = self.delay + random.uniform(0, self.delay / 2) - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.time()

    def get(self, url: str, retries: int = 3) -> FetchResult:
        last_exc: Optional[Exception] = None
        for attempt in range(retries):
            self._polite_wait()
            t0 = time.time()
            try:
                final_url, status, html = self._get(url)
            except Exception as e:
                last_exc = e
                time.sleep(2 ** attempt * 2)
                continue
            res = FetchResult(final_url, status, html, round(time.time() - t0, 2))
            if status in (429, 503):
                time.sleep(2 ** attempt * 5)
                last_exc = BlockedError(f"{status} {url}")
                continue
            if status == 403 or _looks_like_challenge(html):
                raise BlockedError(f"{self.name}: engellendi/challenge (HTTP {status}) {url}")
            return res
        raise last_exc or RuntimeError(url)

    def _get(self, url: str) -> tuple[str, int, str]:
        raise NotImplementedError

    def close(self) -> None:
        pass


def _looks_like_challenge(html: str) -> bool:
    h = html[:5000].lower()
    return ("just a moment" in h and "cloudflare" in h) or "cf-challenge" in h or "challenge-platform" in h


class RequestsFetcher(Fetcher):
    name = "requests"

    def __init__(self, delay: float = 1.5):
        super().__init__(delay)
        import requests
        self.s = requests.Session()
        self.s.headers.update(HEADERS)

    def _get(self, url):
        r = self.s.get(url, timeout=20, allow_redirects=True)
        return r.url, r.status_code, r.text


class ScraplingFetcher(Fetcher):
    name = "scrapling"

    def __init__(self, delay: float = 1.5):
        super().__init__(delay)
        from scrapling.fetchers import Fetcher as SF
        self._sf = SF

    def _get(self, url):
        page = self._sf.get(url, stealthy_headers=True, follow_redirects=True, timeout=20, retries=1)
        return str(page.url), int(page.status), str(page.html_content)


class PlaywrightFetcher(Fetcher):
    name = "playwright"

    def __init__(self, delay: float = 1.5, headless: bool = True):
        super().__init__(delay)
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=headless)
        self._ctx = self._browser.new_context(user_agent=UA, locale="tr-TR")
        self._page = self._ctx.new_page()

    def _get(self, url):
        resp = self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return self._page.url, resp.status if resp else 0, self._page.content()

    def close(self):
        self._ctx.close(); self._browser.close(); self._pw.stop()


BACKENDS = {"requests": RequestsFetcher, "scrapling": ScraplingFetcher, "playwright": PlaywrightFetcher}


def make_fetcher(name: str, delay: float = 1.5) -> Fetcher:
    return BACKENDS[name](delay=delay)
