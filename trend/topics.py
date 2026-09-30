from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from . import config

GENERIC_THEMES: dict[str, list[str]] = {
    "fiyat_zam": ["zam ", "zamlan", "zamm", "fiyat", "pahalı", "ücret", "kampanya", "indirim"],
    "ariza_kalite": ["arıza", "bozul", "çalışmıyor", "sorun", "hata", "kalitesiz", "kırık", "hasar"],
    "musteri_hizmetleri": ["müşteri hizmet", "çağrı merkez", "ulaşamıyorum", "ulaşılamıyor", "servis",
                           "şikayet ettim", "şikayetvar", "muhatap", "kimse ilgilenm", "iade"],
    "bekleme_teslimat": ["gecik", "gelmedi", "bekliyorum", "günlerdir", "haftadır", "teslim", "stok"],
    "olumlu_deneyim": ["memnun", "teşekkür", "sorunsuz", "başarılı", "tavsiye ederim", "harika"],
    "genel_memnuniyetsizlik": ["rezil", "rezalet", "berbat", "en kötü", "sakın", "kullanmayın", "felaket"],
}


def _slug(text: str) -> str:
    t = text.lower().replace("ı", "i").replace("ş", "s").replace("ğ", "g").replace("ü", "u") \
        .replace("ö", "o").replace("ç", "c")
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def keywords_from_label(label: str) -> list[str]:
    parts = re.split(r",|\bve\b|\bile\b|&", label, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()] or [label.strip()]


def build_topic(label: str, keywords: list[str], brands: list[str]) -> dict:
    keywords = [k.strip() for k in keywords if k.strip()]
    brands = [b.strip() for b in brands if b.strip()]
    return {
        "label": label,
        "generated": True,
        "brand_labels": brands,
        "relevance_words": keywords,
        "eksi_topics": brands + keywords,
        "eksi_search_keyword": keywords[0] if keywords else None,
        "eksi_search_keywords": keywords,
        "eksi_exclude_slug": None,
        "x_queries": [f'"{k}" lang:tr -filter:retweets' if " " in k else f"{k} lang:tr -filter:retweets"
                      for k in keywords],
        "tiktok_queries": keywords + brands,
        "instagram_tags": [k.replace(" ", "") for k in keywords + brands],
        "themes": GENERIC_THEMES,
        "brands": {_slug(b).replace("-", "_"): [b.lower()] for b in brands},
        "brand_slugs": {_slug(b): _slug(b).replace("-", "_") for b in brands},
    }


def init_topic(name: str, label: str, keywords: list[str], brands: list[str], force: bool = False) -> Path:
    path = config.TOPICS_DIR / f"{name}.json"
    if path.exists() and not force:
        raise SystemExit(f"{path} zaten var (uzerine yazmak icin --force)")
    path.write_text(json.dumps(build_topic(label, keywords, brands), ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return path
