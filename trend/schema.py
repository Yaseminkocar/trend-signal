from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query)
             if not (k.startswith("utm_") or k in _TRACKING_PARAMS)]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower().removeprefix("www."),
                       path, urlencode(query), ""))


_TRACKING_PARAMS = {"s", "t", "ref", "ref_src", "fbclid", "gclid"}


def record_id(source: str, url: str) -> str:
    return hashlib.sha1(f"{source}|{canonical_url(url)}".encode()).hexdigest()[:16]


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("İ", "i").replace("I", "ı").lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"@\w+", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def content_hash(text: str) -> str:
    return hashlib.sha1(normalize_text(text).encode()).hexdigest()[:16]


@dataclass
class Record:
    source: str
    url: str
    text: str
    published_at: Optional[str]
    collected_at: str
    author: Optional[str] = None
    query: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)
    id: str = ""

    def __post_init__(self) -> None:
        self.url = canonical_url(self.url)
        if not self.id:
            self.id = record_id(self.source, self.url)
        if self.published_at is not None:
            _require_tz(self.published_at, "published_at")
        _require_tz(self.collected_at, "collected_at")

    @property
    def published_dt(self) -> Optional[datetime]:
        return datetime.fromisoformat(self.published_at) if self.published_at else None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Record":
        return cls(**d)


def _require_tz(value: str, name: str) -> None:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError(f"{name} saat dilimi içermeli: {value!r}")
