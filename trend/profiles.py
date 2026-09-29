from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional

from .schema import content_hash


@dataclass
class AccountProfile:
    author: str
    source: str
    collected_at: str
    created_at: Optional[str] = None
    followers: Optional[int] = None
    following: Optional[int] = None
    statuses: Optional[int] = None
    default_image: Optional[bool] = None
    verified: Optional[bool] = None
    handle_digit_suffix: Optional[bool] = None
    recent_texts: list[str] = field(default_factory=list)
    recent_times: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "AccountProfile":
        return cls(**d)


def handle_has_digit_suffix(handle: str) -> bool:
    return bool(re.search(r"\d{4,}$", handle or ""))


@dataclass
class BotVerdict:
    author: str
    score: int
    label: str
    reasons: list[str]
    features: dict


def score_profile(p: AccountProfile, asof: datetime) -> BotVerdict:
    reasons: list[str] = []
    feats: dict = {}
    score = 0
    known = 0

    if p.created_at:
        known += 1
        age = max((asof - datetime.fromisoformat(p.created_at)).days, 1)
        feats["account_age_days"] = age
        if age < 30:
            score += 2; reasons.append(f"hesap çok yeni ({age} gün)")
        elif age < 180:
            score += 1; reasons.append(f"hesap yeni ({age} gün)")
        if p.statuses is not None:
            ppd = p.statuses / age
            feats["lifetime_posts_per_day"] = round(ppd, 1)
            if ppd > 50:
                score += 2; reasons.append(f"ömür boyu günde {ppd:.0f} paylaşım")
            elif ppd > 20:
                score += 1; reasons.append(f"ömür boyu günde {ppd:.0f} paylaşım")

    if len(p.recent_times) >= 5:
        known += 1
        ts = sorted(datetime.fromisoformat(t) for t in p.recent_times)
        span_days = max((ts[-1] - ts[0]).total_seconds() / 86400, 1 / 24)
        rate = len(ts) / span_days
        feats["recent_posts_per_day"] = round(rate, 1)
        if rate > 100:
            score += 1; reasons.append(f"son paylaşımlarda günde ~{rate:.0f} paylaşım hızı")

    if len(p.recent_texts) >= 5:
        known += 1
        hashes = [content_hash(t) for t in p.recent_texts]
        dup_ratio = 1 - len(set(hashes)) / len(hashes)
        feats["recent_duplicate_ratio"] = round(dup_ratio, 2)
        if dup_ratio > 0.5:
            score += 2; reasons.append(f"son paylaşımların %{dup_ratio*100:.0f}'i birbirinin tekrarı")
        elif dup_ratio > 0.3:
            score += 1; reasons.append(f"son paylaşımların %{dup_ratio*100:.0f}'i tekrar")

    if p.followers is not None and p.following is not None:
        known += 1
        feats["followers"] = p.followers
        feats["following"] = p.following
        if p.followers < 10 and p.following > 200:
            score += 1; reasons.append("çok az takipçi, çok fazla takip")

    if p.default_image:
        score += 1; reasons.append("varsayılan profil fotoğrafı")
    if p.handle_digit_suffix:
        score += 1; reasons.append("kullanıcı adı uzun rakam dizisiyle bitiyor")
    if p.verified:
        feats["verified"] = True

    if known == 0:
        return BotVerdict(p.author, score, "yetersiz_veri", ["profil verisine ulaşılamadı"], feats)
    label = "bot_olasi" if score >= 4 else "supheli" if score >= 2 else "gercek_olasi"
    if not reasons:
        reasons = ["belirgin bot işareti yok"]
    return BotVerdict(p.author, score, label, reasons, feats)
