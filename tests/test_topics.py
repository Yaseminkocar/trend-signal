import json

import pytest

from trend import config
from trend.analysis.grouping import assign_brand, assign_theme
from trend.collectors.x import is_relevant
from trend.topics import build_topic
from tests.helpers import rec


@pytest.fixture
def ev_topic():
    config.use_topic("elektrikli_arac")
    yield
    config.use_topic("kargo")


def test_every_topic_file_loads():
    for name in config.available_topics():
        config.use_topic(name)
        assert config.THEMES and config.RELEVANCE_WORDS and config.X_QUERIES
        assert config.RAW_PATH.parent.name == name
    config.use_topic("kargo")


def test_same_code_different_topic(ev_topic):
    assert config.RAW_PATH.as_posix().endswith("data/elektrikli_arac/records.jsonl")
    assert is_relevant("Togg şarj istasyonunda 2 saat bekledim")
    assert not is_relevant("kargom 3 gündür gelmedi")
    assert assign_theme("menzil yazanın yarısı bile değil, şarj bitti")[0] == "sarj_menzil"
    assert assign_brand(rec(1, 1, text="Tesla servisine ulaşamıyorum")) == "tesla"


def test_topic_switch_back_restores_kargo(ev_topic):
    config.use_topic("kargo")
    assert is_relevant("kargom 3 gündür gelmedi")
    assert assign_brand(rec(1, 1, text="hepsijet kuryesi gelmedi")) == "hepsijet"


def test_build_topic_from_keywords():
    t = build_topic("Kahve", ["filtre kahve", "espresso"], ["Starbucks", "Kahve Dünyası"])
    assert t["x_queries"][0] == '"filtre kahve" lang:tr -filter:retweets'
    assert t["brands"]["kahve_dunyasi"] == ["kahve dünyası"]
    assert t["brand_slugs"]["kahve-dunyasi"] == "kahve_dunyasi"
    assert t["instagram_tags"][0] == "filtrekahve"
    json.dumps(t, ensure_ascii=False)


def test_unknown_topic_fails_clearly():
    with pytest.raises(SystemExit):
        config.use_topic("olmayan_konu")
    config.use_topic("kargo")


def test_until_window_for_social_sources():
    from datetime import datetime, timezone
    from trend.collectors.social import _within
    until = datetime(2026, 8, 14, 23, 59, tzinfo=timezone.utc)
    inside = rec(1, 0)
    inside.published_at = "2026-08-05T10:00:00+00:00"
    late = rec(2, 0)
    late.published_at = "2026-09-20T10:00:00+00:00"
    early = rec(3, 0)
    early.published_at = "2026-07-01T10:00:00+00:00"
    assert _within(inside, 14, until) and not _within(late, 14, until) and not _within(early, 14, until)


def test_cli_accepts_topic_and_until(monkeypatch):
    from trend import cli
    seen = {}
    monkeypatch.setattr(cli, "cmd_collect", lambda a: seen.update(topic=config.TOPIC, until=a.until))
    cli.main(["--topic", "elektrikli_arac", "collect", "eksi", "--until", "2026-08-14"])
    assert seen["topic"] == "elektrikli_arac" and str(seen["until"]) == "2026-08-14"
    config.use_topic("kargo")
