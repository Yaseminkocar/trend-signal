from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterator, Optional
from urllib.parse import quote_plus, urljoin, urlsplit

from bs4 import BeautifulSoup

from .. import config
from ..fetchers import BlockedError, Fetcher
from ..issues import log_issue
from ..privacy import mask_mentions, mask_user
from ..schema import Record, now_utc_iso

BASE = "https://eksisozluk.com"
SOURCE = "eksi"
_DATE_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})(?:\s+(\d{2}):(\d{2}))?")


def parse_eksi_date(text: str) -> tuple[Optional[str], Optional[str]]:
    m = _DATE_RE.search(text or "")
    if not m:
        return None, None
    d, mo, y, hh, mm = m.groups()
    day = f"{y}-{mo}-{d}"
    if hh is None:
        return None, day
    dt = datetime(int(y), int(mo), int(d), int(hh), int(mm), tzinfo=config.TR_TZ)
    return dt.isoformat(), day


def parse_topic_page(html: str, page_url: str, collected_at: str, topic: str) -> tuple[list[Record], int, int]:
    soup = BeautifulSoup(html, "lxml")
    pager = soup.select_one("div.pager")
    cur_page = int(pager.get("data-currentpage", 1)) if pager else 1
    page_count = int(pager.get("data-pagecount", 1)) if pager else 1

    out = []
    for li in soup.select("ul#entry-item-list > li"):
        entry_id = li.get("data-id")
        content = li.select_one("div.content")
        if not entry_id or content is None:
            continue
        for br in content.find_all("br"):
            br.replace_with("\n")
        text = content.get_text(" ", strip=True)
        date_a = li.select_one("a.entry-date")
        published_at, pub_day = parse_eksi_date(date_a.get_text(" ", strip=True) if date_a else "")
        author = li.get("data-author") or (li.select_one("a.entry-author").get_text(strip=True)
                                           if li.select_one("a.entry-author") else None)
        out.append(Record(
            source=SOURCE,
            url=f"{BASE}/entry/{entry_id}",
            text=mask_mentions(text),
            published_at=published_at,
            collected_at=collected_at,
            author=mask_user(author),
            query=topic,
            extra={"topic_url": page_url.split("?")[0], "published_date": pub_day,
                   "favorite_count": _int(li.get("data-favorite-count")),
                   "edited": bool(date_a and "~" in date_a.get_text())},
        ))
    return out, cur_page, page_count


def _int(v) -> Optional[int]:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def resolve_topic_url(fetcher: Fetcher, topic: str) -> Optional[str]:
    res = fetcher.get(f"{BASE}/?q={quote_plus(topic)}")
    path = urlsplit(res.url).path
    if re.search(r"--\d+$", path):
        return BASE + path
    soup = BeautifulSoup(res.html, "lxml")
    h1 = soup.select_one("h1#title a")
    if h1 and h1.get("href"):
        return urljoin(BASE, h1["href"].split("?")[0])
    log_issue(SOURCE, "baslik_bulunamadi", f"'{topic}' için başlık yok ({res.url})",
              "başlık atlandı")
    return None


def discover_topics(fetcher: Fetcher, keyword: str, since: date, until: date,
                    save_html: Path | None = None) -> list[str]:
    url = (f"{BASE}/basliklar/ara?SearchForm.Keywords={quote_plus(keyword)}"
           f"&SearchForm.When.From={since.isoformat()}&SearchForm.When.To={until.isoformat()}"
           f"&SearchForm.NiceOnly=false&SearchForm.SortOrder=Date")
    try:
        res = fetcher.get(url)
    except Exception as e:
        log_issue(SOURCE, "arama_hatasi", f"{url}: {e}", "sadece config'teki başlıklar kullanıldı")
        return []
    if save_html:
        save_html.write_text(res.html, encoding="utf-8")
    soup = BeautifulSoup(res.html, "lxml")
    out = []
    for a in soup.select("ul.topic-list li a[href]"):
        href = a["href"].split("?")[0]
        if re.search(r"--\d+$", href):
            if re.search(config.EKSI_EXCLUDE_SLUG, href):
                log_issue(SOURCE, "konu_disi_baslik", href, "config.EKSI_EXCLUDE_SLUG ile elendi")
                continue
            out.append(urljoin(BASE, href))
    if not out:
        log_issue(SOURCE, "arama_bos", f"'{keyword}' araması başlık döndürmedi ({res.status})",
                  "sadece config'teki başlıklar kullanıldı")
    return list(dict.fromkeys(out))


def slug_matches(url: str, keyword: str) -> bool:
    from ..topics import _slug
    words = urlsplit(url).path.strip("/").split("--")[0].split("-")
    tokens = [t for t in _slug(keyword).split("-") if t]
    return bool(tokens) and all(any(w.startswith(t) for w in words) for t in tokens)


def find_topics(fetcher: Fetcher, keyword: str, since: date, until: date,
                save_html: Path | None = None) -> list[str]:
    found = discover_topics(fetcher, keyword, since, until, save_html)
    if found:
        return found
    from ..topics import _slug
    tokens = sorted((t for t in _slug(keyword).split("-") if len(t) >= 3), key=len, reverse=True)
    if not tokens or tokens[0] == _slug(keyword):
        return []
    broad = discover_topics(fetcher, tokens[0], since, until)
    matched = [u for u in broad if slug_matches(u, keyword)]
    if matched:
        log_issue(SOURCE, "genis_arama", f"'{keyword}' -> '{tokens[0]}' ile arandi, {len(matched)} baslik eslesti",
                  "tam ifade baslik dondurmedi, kelimeleri iceren basliklar alindi")
    return matched


def collect(fetcher: Fetcher, topics: list[str] | None = None, days: int = 14,
            max_pages: int = 30, discover: bool = True, max_discovered: int = 25,
            today: date | None = None, save_html_dir: Path | None = None) -> Iterator[Record]:
    topics = config.EKSI_TOPICS if topics is None else topics
    today = today or datetime.now(config.TR_TZ).date()
    cutoff = today - timedelta(days=days + 1)

    urls: list[tuple[str, str]] = []
    for topic in topics:
        try:
            u = resolve_topic_url(fetcher, topic)
        except BlockedError as e:
            log_issue(SOURCE, "engellendi", str(e), "başka araçla (--backend) tekrar denenmeli")
            raise
        if u:
            urls.append((topic, u))
    if discover:
        known = {u for _, u in urls}
        for kw in config.EKSI_SEARCH_KEYWORDS[:4]:
            found = find_topics(fetcher, kw, cutoff, today,
                                save_html_dir / "eksi_search.html" if save_html_dir else None)
            print(f"[eksi] '{kw}' aramasıyla bulunan aktif başlık: {len(found)}")
            for u in found:
                if u not in known and len(known) < len(topics) + max_discovered:
                    urls.append((f"arama:{kw}", u))
                    known.add(u)

    for topic, url in urls:
        try:
            first = fetcher.get(url)
        except BlockedError as e:
            log_issue(SOURCE, "engellendi", str(e), "kalan başlıklar atlandı"); return
        except Exception as e:
            log_issue(SOURCE, "ag_hatasi", f"{url}: {e}", "başlık atlandı"); continue
        if save_html_dir and topic == urls[0][0]:
            (save_html_dir / "eksi_topic_p1.html").write_text(first.html, encoding="utf-8")
        _, _, page_count = parse_topic_page(first.html, url, now_utc_iso(), topic)
        print(f"[eksi] {topic} -> {url} ({page_count} sayfa)")
        page, fetched = page_count, 0
        while page >= 1 and fetched < max_pages:
            page_url = url if page == 1 else f"{url}?p={page}"
            try:
                html = first.html if page == 1 else fetcher.get(page_url).html
            except BlockedError as e:
                log_issue(SOURCE, "engellendi", str(e), "kalan sayfalar atlandı"); return
            except Exception as e:
                log_issue(SOURCE, "ag_hatasi", f"{page_url}: {e}", "sayfa atlandı"); break
            recs, _, _ = parse_topic_page(html, page_url, now_utc_iso(), topic)
            fetched += 1
            if not recs:
                log_issue(SOURCE, "bos_sayfa", page_url, "başlık sonlandırıldı"); break
            yield from recs
            days_seen = [r.extra.get("published_date") for r in recs if r.extra.get("published_date")]
            if days_seen and min(days_seen) < cutoff.isoformat():
                break
            page -= 1
        else:
            if fetched >= max_pages:
                log_issue(SOURCE, "sayfalama_limiti", f"{topic}: {max_pages} sayfada kesime ulaşılamadı",
                          "başlığın eski kısmı eksik (önceki dönem hacmi alt sınır)")
