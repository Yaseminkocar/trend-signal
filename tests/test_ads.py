import csv
import json
from pathlib import Path

from trend.analysis.ads import fold, is_ad
from trend.analysis.signal import share_check, split_periods
from tests.helpers import ASOF, rec

ROOT = Path(__file__).resolve().parents[1]


def test_fold_turkish_letters():
    assert fold("ÖZEL Çözüm İŞ Işık") == "ozel cozum is isik"


def test_seller_post_is_ad():
    ad, why = is_ad("Eşarp fiyat: 145₺ WhatsApp sipariş hattı [tel] kapıda ödeme, 750₺ üzeri kargo bedava")
    assert ad and any(w.startswith("fiyat") for w in why)


def test_corporate_post_is_ad():
    assert is_ad("Tüm gönderileriniz için hizmetinizdeyiz, lojistik çözümler sunuyoruz. Siparişleriniz güvende")[0]


def test_complaint_with_product_words_is_kept():
    text = "Gönderdiğim ürünler hep kırık geliyor, müşterilerimden özür diliyorum, ptt kargo pişmanlıktır"
    assert not is_ad(text)[0]


def test_hashtag_only_complaint_is_kept():
    assert not is_ad("#keşfet #kargo #şikayetimvar #kargomgeldi #keşfet")[0]


def test_personal_story_is_kept():
    assert not is_ad("kargom 12 gündür gelmedi, arayınca kimse bilmiyor")[0]


def test_share_check_blocks_recency_bias():
    prev = [rec(i, 9, source="instagram") for i in range(10)]
    cur = [rec(100 + i, 2, source="instagram") for i in range(30)]
    group_prev, group_cur = prev[:2], cur[:6]
    c, p, _, _ = split_periods(group_prev + group_cur, ASOF)
    s_prev, s_cur, chk = share_check(c, p, (len(cur), len(prev)))
    assert (s_prev, s_cur) == (0.2, 0.2)
    assert not chk.passed


def test_share_check_skips_unsampled_groups():
    rs = [rec(i, 2, source="eksi") for i in range(5)]
    assert share_check(rs, [], (10, 10)) == (None, None, None)


def test_hand_labels_accuracy():
    records = {}
    for line in (ROOT / "data/kargo/records.jsonl").read_text(encoding="utf-8").split("\n"):
        if not line.strip():
            continue
        r = json.loads(line)
        records[r["url"]] = r["text"]
    tp = fp = fn = 0
    with open(ROOT / "data/kargo/ad_labels.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if not row["url"]:
                continue
            pred, gold = is_ad(records[row["url"]])[0], row["etiket"] == "ticari"
            tp += pred and gold
            fp += pred and not gold
            fn += gold and not pred
    assert tp / (tp + fp) >= 0.9
    assert tp / (tp + fn) >= 0.8


def test_share_check_skips_group_covering_all_sampled():
    cur = [rec(i, 2, source="x") for i in range(6)]
    prev = [rec(100 + i, 9, source="x") for i in range(3)]
    assert share_check(cur, prev, (6, 3)) == (None, None, None)
