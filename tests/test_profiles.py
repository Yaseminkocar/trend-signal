from datetime import timedelta

from trend.privacy import mask_mentions, mask_user
from trend.profiles import AccountProfile, handle_has_digit_suffix, score_profile
from tests.helpers import ASOF, COLLECTED


def _iso(days_ago: float) -> str:
    return (ASOF - timedelta(days=days_ago)).isoformat()


def test_real_looking_account():
    p = AccountProfile("u_a", "x", COLLECTED, created_at=_iso(2000), followers=300, following=250,
                       statuses=4000, default_image=False, handle_digit_suffix=False,
                       recent_texts=[f"farklı tweet {i} konu {i*3}" for i in range(10)],
                       recent_times=[_iso(i * 2) for i in range(10)])
    v = score_profile(p, ASOF)
    assert v.label == "gercek_olasi", v.reasons


def test_bot_looking_account():
    p = AccountProfile("u_b", "x", COLLECTED, created_at=_iso(12), followers=2, following=900,
                       statuses=3000, default_image=True, handle_digit_suffix=True,
                       recent_texts=["aynı reklam metni"] * 8 + ["x", "y"],
                       recent_times=[_iso(i * 0.01) for i in range(10)])
    v = score_profile(p, ASOF)
    assert v.label == "bot_olasi"
    assert any("yeni" in r for r in v.reasons) and any("tekrar" in r for r in v.reasons)


def test_no_profile_data():
    assert score_profile(AccountProfile("u_c", "x", COLLECTED), ASOF).label == "yetersiz_veri"


def test_masking_is_stable_and_irreversible():
    assert mask_user("@Ayse_K", "s") == mask_user("ayse_k", "s")
    assert "ayse" not in mask_user("ayse_k", "s")
    assert "@ayse_k" not in mask_mentions("merhaba @ayse_k nasılsın", "s")
    assert handle_has_digit_suffix("mehmet48213") and not handle_has_digit_suffix("mehmet48")
