import json

import pytest

from trend import store
from trend.schema import Record, canonical_url, record_id
from tests.helpers import COLLECTED, rec


def test_rerun_does_not_duplicate(tmp_path):
    path = tmp_path / "records.jsonl"
    batch = [rec(i, 1) for i in range(10)]
    assert store.upsert(path, batch) == (10, 0)
    again = [rec(i, 1) for i in range(10)]
    assert store.upsert(path, again) == (0, 10)
    assert len(store.load(path)) == 10
    assert len(path.read_text().strip().splitlines()) == 10


def test_same_post_different_url_forms_is_one_record(tmp_path):
    path = tmp_path / "records.jsonl"
    a = Record("x", "https://x.com/u/status/123?s=20&t=abc", "metin", None, COLLECTED)
    b = Record("x", "https://www.x.com/u/status/123/", "metin", None, COLLECTED)
    assert a.id == b.id
    store.upsert(path, [a])
    assert store.upsert(path, [b]) == (0, 1)


def test_first_collected_at_kept_and_missing_date_backfilled(tmp_path):
    path = tmp_path / "records.jsonl"
    first = Record("eksi", "https://eksisozluk.com/entry/1", "t", None, COLLECTED)
    store.upsert(path, [first])
    later = Record("eksi", "https://eksisozluk.com/entry/1", "t",
                   "2026-09-28T10:00:00+03:00", "2026-09-30T09:00:00+00:00")
    store.upsert(path, [later])
    [r] = store.load(path)
    assert r.collected_at == COLLECTED
    assert r.published_at == "2026-09-28T10:00:00+03:00"


def test_missing_published_at_stays_empty(tmp_path):
    path = tmp_path / "records.jsonl"
    store.upsert(path, [rec(1, None)])
    raw = json.loads(path.read_text())
    assert raw["published_at"] is None


def test_naive_datetime_rejected():
    with pytest.raises(ValueError):
        Record("x", "https://x.com/a/status/1", "t", "2026-09-28T10:00:00", COLLECTED)


def test_canonical_url_keeps_meaningful_params():
    assert canonical_url("https://eksisozluk.com/kargo--123?p=5&utm_source=x") == \
        "https://eksisozluk.com/kargo--123?p=5"
    assert record_id("x", "https://x.com/a/status/1") != record_id("eksi", "https://x.com/a/status/1")
