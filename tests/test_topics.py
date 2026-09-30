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


def test_run_creates_topic_then_collects_and_analyzes(tmp_path, monkeypatch):
    import shutil
    from trend import cli
    for f in config.TOPICS_DIR.glob("*.json"):
        shutil.copy(f, tmp_path / f.name)
    monkeypatch.setattr(config, "TOPICS_DIR", tmp_path)
    calls = []
    monkeypatch.setattr(cli, "cmd_collect", lambda a: calls.append(("collect", config.TOPIC, a.source)))
    monkeypatch.setattr(cli, "cmd_analyze", lambda a: calls.append(("analyze", config.TOPIC, a.sources)))
    cli.main(["run", "Filtre Kahve", "--brands", "Starbucks,Kahve Dünyası", "--collect", "eksi,x"])
    assert (tmp_path / "filtre_kahve.json").exists()
    assert calls == [("collect", "filtre_kahve", "eksi"), ("collect", "filtre_kahve", "x"),
                     ("analyze", "filtre_kahve", "eksi,x")]
    config.use_topic("kargo")


def test_keywords_from_label():
    from trend.topics import keywords_from_label
    assert keywords_from_label("apple ve telefon fiyatları") == ["apple", "telefon fiyatları"]
    assert keywords_from_label("kahve, çay") == ["kahve", "çay"]
    assert keywords_from_label("elektrikli scooter") == ["elektrikli scooter"]
