from __future__ import annotations

import re

_FOLD = str.maketrans("ıiğüşöçâîû", "iigusocaiu")

RULES: dict[str, list[str]] = {
    "fiyat": [r"\d[\d.,]*\s*(₺|tl\b)", r"\bfiyat", r"\bdesi\b"],
    "siparis_iletisim": [r"\bsiparis", r"whatsap", r"\bdm\b", r"\[tel\]", r"www\.", r"\.com\b", r"profil(deki|den)",
                         r"mesaj\s+bolum", r"bilgi\s+(ve|icin)", r"iletisim", r"hikaye(mizdeki|deki)\s+baglanti"],
    "satis_kosulu": [r"kapida\s+(nakit\s+)?odeme", r"\bhavale", r"\beft\b", r"taksit", r"kargo\s+bedava",
                     r"ucretsiz\s+kargo", r"kargo\s+ucret", r"uzeri", r"toptan", r"\bbeden", r"\bstok",
                     r"minimum", r"adet", r"\burun"],
    "kampanya": [r"indirim", r"kampanya", r"%\s?\d", r"\d\s?%", r"cekilis", r"avantajli", r"ucretsiz"],
    "kurumsal_dil": [r"hizmet", r"cozum", r"is\s+ortak", r"sunuyoruz", r"ulastiriyoruz", r"olarak\s",
                     r"birimimiz", r"subesi", r"sozverdigimizgibi", r"lojistik", r"tasimacilik", r"sponsor",
                     r"tercih\s+ettiginiz", r"yaninizda", r"gonderileriniz", r"siparisleriniz", r"musterilerimiz",
                     r"genel\s+mudur", r"e-ticaret", r"entegrasyon"],
    "is_ilani": [r"personel", r"is\s+ilani", r"isilani", r"aranmaktadir", r"pozisyon", r"basvuru", r"\bilan"],
}

COMPLAINT = [r"gelmedi", r"teslim\s+edemedi", r"magdur", r"sikayet", r"kirik", r"rezil", r"pisman", r"eksik",
             r"\bsorun", r"ilgisiz", r"sacma", r"hala\s", r"yaziklar", r"bekliyoruz", r"kayip", r"gecikti"]

_HASHTAG = re.compile(r"#\S+")


def fold(text: str) -> str:
    return (text or "").replace("İ", "i").replace("I", "ı").lower().translate(_FOLD)


def ad_reasons(text: str) -> tuple[int, list[str]]:
    t = fold(text)
    reasons = []
    score = 0
    for name, pats in RULES.items():
        hits = sum(bool(re.search(p, t)) for p in pats)
        if hits:
            reasons.append(name if hits == 1 else f"{name}x{min(hits, 2)}")
            score += min(hits, 2)
    words_all = re.findall(r"[a-z]+", t)
    we = sum(bool(re.search(r"(imiz|umuz|iyoruz|uyoruz|iriz|uruz)\w{0,3}$", w)) for w in words_all)
    you = sum(bool(re.search(r"(iniz|unuz)\w{0,3}$", w)) for w in words_all)
    if we >= 2:
        reasons.append("biz_dili"); score += 1
    if you >= 2:
        reasons.append("size_hitap"); score += 1
    tags = _HASHTAG.findall(t)
    words = [w for w in _HASHTAG.sub(" ", t).split() if any(ch.isalpha() for ch in w)]
    if len(tags) >= 3 and len(words) <= 6:
        reasons.append("etiket_yigini"); score += 1
    if any(re.search(p, t) for p in COMPLAINT):
        score -= 3
        reasons.append("sikayet_dili(-3)")
    return score, reasons


def is_ad(text: str, threshold: int = 2) -> tuple[bool, list[str]]:
    score, reasons = ad_reasons(text)
    return score >= threshold, reasons
