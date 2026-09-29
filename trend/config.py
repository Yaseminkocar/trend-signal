from __future__ import annotations

import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
TOPICS_DIR = ROOT / "topics"

TR_TZ = ZoneInfo("Europe/Istanbul")

EKSI_DAYS = 14
EKSI_MAX_PAGES_PER_TOPIC = 30
SIGNAL_SOURCES = ("eksi", "x")
X_TWEETS_PER_DAY = 25
X_PROFILE_HISTORY = 20

MIN_UNIQUE_CURRENT = 5
MIN_AUTHORS_CURRENT = 3
MIN_ACTIVE_DAYS_CURRENT = 3
MAX_SINGLE_DAY_SHARE = 0.6
MIN_SOURCES = 2
RISE_THRESHOLD = 1.0


def available_topics() -> list[str]:
    return sorted(p.stem for p in TOPICS_DIR.glob("*.json"))


def use_topic(name: str) -> None:
    path = TOPICS_DIR / f"{name}.json"
    if not path.exists():
        raise SystemExit(f"konu bulunamadi: {name} (mevcut: {', '.join(available_topics())})")
    t = json.loads(path.read_text(encoding="utf-8"))
    g = globals()
    g["TOPIC"] = name
    g["TOPIC_LABEL"] = t.get("label", name)
    g["RELEVANCE_WORDS"] = t.get("relevance_words", [])
    g["EKSI_TOPICS"] = t.get("eksi_topics", [])
    g["EKSI_SEARCH_KEYWORD"] = t.get("eksi_search_keyword")
    g["EKSI_EXCLUDE_SLUG"] = t.get("eksi_exclude_slug") or r"(?!)"
    g["X_QUERIES"] = t.get("x_queries", [])
    g["TIKTOK_QUERIES"] = t.get("tiktok_queries", [])
    g["INSTAGRAM_TAGS"] = t.get("instagram_tags", [])
    g["THEMES"] = t.get("themes", {})
    g["BRANDS"] = t.get("brands", {})
    g["BRAND_SLUGS"] = t.get("brand_slugs", {})
    g["DATA_DIR"] = ROOT / "data" / name
    g["RAW_PATH"] = g["DATA_DIR"] / "records.jsonl"
    g["PROFILES_PATH"] = g["DATA_DIR"] / "profiles.jsonl"
    g["ISSUE_LOG"] = g["DATA_DIR"] / "issues.jsonl"
    g["OUTPUT_DIR"] = ROOT / "output" / name


use_topic(os.getenv("TREND_TOPIC", "kargo"))
