import json
from datetime import datetime, timezone
from pathlib import Path

from trend.collectors.eksi import parse_eksi_date, parse_topic_page
from trend.collectors.x import build_profile, day_queries, parse_tweet_result, parse_x_date
from trend.privacy import mask_user
from trend.profiles import score_profile

FIX = Path(__file__).parent / "fixtures"
COLLECTED = "2026-09-29T12:00:00+00:00"


def test_eksi_page_parsing():
    html = (FIX / "eksi_topic.html").read_text(encoding="utf-8")
    recs, cur, count = parse_topic_page(html, "https://eksisozluk.com/yurtici-kargo--123456?day=2026-09-27",
                                        COLLECTED, "yurtiçi kargo")
    assert (cur, count, len(recs)) == (1, 2, 4)
    a, b, c, d = recs
    assert a.url == "https://eksisozluk.com/entry/170000001"
    assert a.published_at == "2026-09-27T14:32:00+03:00"
    assert "transfer merkezinde" in a.text and "\n" not in a.text[:5]
    assert a.author == mask_user("kargocu_ayse") and "kargocu_ayse" not in json.dumps(a.to_dict())
    assert "baska_yazar" not in a.text
    assert b.published_at == "2026-09-28T09:05:00+03:00" and b.extra["edited"]
    assert c.published_at is None and c.extra["published_date"] == "2004-02-01"
    assert d.published_at is None and d.extra["published_date"] is None


def test_eksi_date_formats():
    assert parse_eksi_date("29.09.2026 00:01")[0] == "2026-09-29T00:01:00+03:00"
    assert parse_eksi_date("") == (None, None)


def test_x_parsing_and_retweet_skip():
    data = json.loads((FIX / "x_search_results.json").read_text(encoding="utf-8"))
    parsed = [parse_tweet_result(d, COLLECTED, "q") for d in data]
    assert parsed[2] is None
    (r1, u1), (r2, u2) = parsed[0], parsed[1]
    assert r1.url == "https://x.com/i/status/1971000000000000001"
    assert r1.published_at == "2026-09-26T08:15:00+00:00"
    assert "yurticikargo" not in r1.text
    assert r1.author == mask_user("ali_veli")
    assert u2["screen_name"] == "bot12345678"
    assert u2["default_image"] is True


def test_x_profile_from_search_fields_flags_new_account():
    data = json.loads((FIX / "x_search_results.json").read_text(encoding="utf-8"))
    rec, user = parse_tweet_result(data[1], COLLECTED, "q")
    prof = build_profile(user, [], COLLECTED)
    v = score_profile(prof, datetime(2026, 9, 29, tzinfo=timezone.utc))
    assert v.label in ("supheli", "bot_olasi")
    assert any("yeni" in r for r in v.reasons)


def test_x_day_split_covers_both_periods():
    from datetime import date
    qs = day_queries("kargo", 14, date(2026, 9, 29))
    assert len(qs) == 15
    assert qs[0][1].endswith("since:2026-09-29 until:2026-09-30")
    assert qs[-1][0] == "2026-09-15"


def test_parse_x_date_bad_input():
    assert parse_x_date(None) is None and parse_x_date("dün") is None


class _FakeFetcher:
    def __init__(self):
        self.calls = []

    def get(self, url):
        from trend.fetchers import FetchResult
        self.calls.append(url)
        page = int(url.split("?p=")[1]) if "?p=" in url else 1
        items = []
        for i in range(10):
            day = 30 - (5 - page) * 4 - (9 - i) // 5
            items.append(f'<li data-id="{page}{i:02d}" data-author="a{i}"><div class="content">kargo {page}-{i}</div>'
                         f'<a class="entry-date">{day:02d}.09.2026 10:00</a></li>')
        html = (f'<div class="pager" data-currentpage="{page}" data-pagecount="5"></div>'
                f'<ul id="entry-item-list">{"".join(items)}</ul>')
        return FetchResult(url, 200, html, 0.0)


def test_eksi_backward_pagination_stops_at_cutoff():
    from datetime import date
    from trend.collectors import eksi
    f = _FakeFetcher()
    orig = eksi.resolve_topic_url
    eksi.resolve_topic_url = lambda fetcher, t: "https://eksisozluk.com/kargo--1"
    try:
        recs = list(eksi.collect(f, topics=["kargo"], days=10, discover=False, today=date(2026, 9, 30)))
    finally:
        eksi.resolve_topic_url = orig
    pages = [c for c in f.calls if "?p=" in c]
    assert pages == ["https://eksisozluk.com/kargo--1?p=5", "https://eksisozluk.com/kargo--1?p=4",
                     "https://eksisozluk.com/kargo--1?p=3", "https://eksisozluk.com/kargo--1?p=2"]
    assert len(recs) == 40


def test_extract_tweet_results_from_nested_graphql():
    from trend.collectors.x import extract_tweet_results
    data = json.loads((FIX / "x_search_results.json").read_text(encoding="utf-8"))
    wrapped = {"data": {"search_by_raw_query": {"search_timeline": {"timeline": {"instructions": [
        {"type": "TimelineAddEntries", "entries": [
            {"content": {"itemContent": {"tweet_results": {"result": d}}}} for d in data]}]}}}}}
    found = extract_tweet_results(wrapped)
    assert len(found) == 3
    parsed = [p for p in (parse_tweet_result(f, COLLECTED, "q") for f in found) if p]
    assert len(parsed) == 2


def test_x_relevance_day_and_query_filters():
    from trend.collectors.x import in_day, is_relevant, response_query
    assert is_relevant("Aras kargo paketimi kaybetti")
    assert is_relevant("kargom 3 gündür gelmedi")
    assert not is_relevant("Çeyrek finalistler belli oldu, ACE sayısı rekor")
    data = json.loads((FIX / "x_search_results.json").read_text(encoding="utf-8"))
    rec, _ = parse_tweet_result(data[0], COLLECTED, "q")
    assert in_day(rec, "2026-09-26") and not in_day(rec, "2026-09-27")
    late = rec.__class__(**{**rec.to_dict(), "published_at": "2026-09-28T21:30:00+00:00"})
    assert in_day(late, "2026-09-29")
    url = ('https://x.com/i/api/graphql/abc/SearchTimeline?variables=%7B%22rawQuery%22%3A%22kargo%20'
           'since%3A2026-09-28%22%2C%22count%22%3A20%7D&features=%7B%7D')
    assert response_query(url) == "kargo since:2026-09-28"
    post = json.dumps({"variables": {"rawQuery": "kargo since:2026-09-27"}})
    assert response_query("https://x.com/i/api/graphql/abc/SearchTimeline", post) == "kargo since:2026-09-27"


def test_user_fields_2026_schema():
    from trend.collectors.x import _user_fields
    u = {"rest_id": "1", "core": {"screen_name": "kitapci", "created_at": "Sun Dec 14 20:16:08 +0000 2014"},
         "relationship_counts": {"followers": 184, "following": 944}, "tweet_counts": {"tweets": 3497},
         "verification": {"verified": False}, "avatar": {"image_url": "https://pbs.twimg.com/profile_images/1/a.jpg"}}
    f = _user_fields(u)
    assert (f["followers"], f["following"], f["statuses"], f["default_image"]) == (184, 944, 3497, False)


def test_graphql_op_parsing_never_raises():
    from trend.collectors.x import graphql_op
    assert graphql_op("https://x.com/i/api/graphql/uGB-gN/SearchTimeline?variables=%7B%7D") == "SearchTimeline"
    assert graphql_op("https://x.com/i/api/graphql/abc") is None
    assert graphql_op("https://x.com/i/api/graphql/") is None
    assert graphql_op("https://abs.twimg.com/x.js") is None


def test_tiktok_items():
    from trend.collectors.social import parse_tiktok_items
    data = json.loads((FIX / "tiktok_search.json").read_text(encoding="utf-8"))
    recs = parse_tiktok_items(data, COLLECTED, "kargo")
    assert len(recs) == 2
    r = recs[0]
    assert r.url == "https://tiktok.com/@/video/7555000000000000001"
    assert r.published_at.endswith("+00:00")
    assert r.author == mask_user("ayse.k") and "kargocu" not in r.text


def test_instagram_items():
    from trend.collectors.social import parse_instagram_items
    data = json.loads((FIX / "instagram_tag.json").read_text(encoding="utf-8"))
    [r] = parse_instagram_items(data, COLLECTED, "kargo")
    assert r.url == "https://instagram.com/p/DAbc123"
    assert r.author == mask_user("mehmet_1")
    assert r.published_at is not None
