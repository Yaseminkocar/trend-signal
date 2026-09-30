from datetime import timedelta

from trend.analysis.grouping import assign_theme, near_duplicate_clusters
from trend.analysis.signal import analyze, log_ratio, split_periods
from tests.helpers import ASOF, rec


def _group(result, name="TUMU"):
    return next(g for g in result["groups"] if g.group == name)


def _organic_rise():
    prev = [rec(i, 8.5 + 2 * i) for i in range(3)]
    cur = [rec(100 + i, 0.5 + (i % 5), source="x" if i % 2 else "eksi") for i in range(10)]
    return prev + cur


def test_period_boundaries():
    rs = [rec(1, 7.0), rec(2, 6.999), rec(3, 14.0), rec(4, 14.01), rec(5, None), rec(6, 0.0)]
    cur, prev, undated, older = split_periods(rs, ASOF)
    ids = lambda xs: sorted(int(r.url.rsplit("/", 1)[1]) for r in xs)
    assert ids(cur) == [1, 2]
    assert ids(prev) == [3]
    assert ids(older) == [4, 6]
    assert ids(undated) == [5]


def test_two_period_comparison_detects_organic_rise():
    g = _group(analyze(_organic_rise(), ASOF))
    assert (g.raw_previous, g.raw_current) == (3, 10)
    assert g.clean_score == log_ratio(10, 3) > 1
    assert g.status == "yukselis_adayi"
    assert g.evidence and all(e["url"] and e["published_at"] for e in g.evidence)


def test_artificial_duplicates_do_not_create_fake_rise():
    base = [rec(i, 9 + i % 4) for i in range(4)] + [rec(50 + i, 1 + i) for i in range(4)]
    spam_text = "YURTİÇİ KARGO rezalet!!! paketim gelmedi #kargo https://t.co/abc"
    spam = [rec(200 + i, 1.2, text=spam_text + f" @kisi{i}", author="u_spam") for i in range(30)]
    g = _group(analyze(base + spam, ASOF))
    assert g.raw_current == 34 and g.raw_score > 2
    assert g.unique_current == 5
    assert g.clean_score < 1 and g.status == "yukselis_yok"
    assert g.duplicate_effect > 2


def test_bot_accounts_are_excluded():
    base = [rec(i, 9 + i % 4) for i in range(4)] + [rec(50 + i, 1 + i) for i in range(4)]
    bot_posts = [rec(300 + i, 1 + (i % 5), author="u_bot") for i in range(20)]
    without = _group(analyze(base + bot_posts, ASOF))
    with_bots = _group(analyze(base + bot_posts, ASOF, bots={"u_bot"}))
    assert without.clean_score > 1
    assert with_bots.clean_score < 1


def test_single_source_rise_is_unverified():
    prev = [rec(i, 10) for i in range(2)]
    cur = [rec(100 + i, 0.5 + i % 5, source="eksi") for i in range(10)]
    g = _group(analyze(prev + cur, ASOF))
    assert g.clean_score > 1
    assert g.status == "dogrulanamadi"
    assert any("kaynak" in m for m in g.missing)


def test_too_few_records_is_unverified():
    g = _group(analyze([rec(1, 2, source="x"), rec(2, 3, source="eksi")], ASOF))
    assert g.clean_score > 1
    assert g.status == "dogrulanamadi"
    assert any("tekil içerik" in m for m in g.missing)


def test_single_day_burst_is_unverified():
    prev = [rec(i, 10) for i in range(2)]
    cur = [rec(100 + i, 1.1 + i * 0.01, source="x" if i % 2 else "eksi") for i in range(10)]
    g = _group(analyze(prev + cur, ASOF))
    assert g.status == "dogrulanamadi"
    assert any("gün" in m for m in g.missing)


def test_undated_records_counted_but_not_assigned():
    res = analyze(_organic_rise() + [rec(900, None), rec(901, None)], ASOF)
    assert res["totals"]["undated"] == 2
    assert _group(res).raw_current == 10


def test_theme_keywords_match_word_starts_only():
    assert assign_theme("kargom hala gelmedi, 5 gündür bekliyorum")[0] == "gecikme"
    assert assign_theme("kargo ücretine yine zam gelmiş")[0] == "ucret_zam"
    assert assign_theme("zaman zaman kargo kullanırım")[0] == "diger"


def test_near_duplicate_clustering():
    a = rec(1, 1, text="Aras kargo paketimi 5 gündür teslim etmedi, rezalet bir hizmet")
    b = rec(2, 1, text="aras kargo paketimi 5 gündür teslim etmedi rezalet bir hizmet!!")
    c = rec(3, 1, text="MNG kargo bugün erken geldi, teşekkürler")
    cl = near_duplicate_clusters([a, b, c])
    assert cl[a.id] == cl[b.id] != cl[c.id]


def test_carrier_from_eksi_topic_and_text():
    from trend.analysis.grouping import assign_brand
    from trend.schema import Record
    r = Record("eksi", "https://eksisozluk.com/entry/1", "3 gündür şubede bekliyor", None,
               "2026-09-29T12:00:00+00:00", extra={"topic_url": "https://eksisozluk.com/aras-kargo--45661"})
    assert assign_brand(r) == "aras"
    x1 = rec(1, 1, text="hepsijet kuryesi kapıya gelmedi")
    x2 = rec(2, 1, text="yurtiçi hızlı ama aras kargo yavaş")
    x3 = rec(3, 1, text="kargom hala yok")
    assert (assign_brand(x1), assign_brand(x2), assign_brand(x3)) == \
        ("hepsijet", "coklu_firma", "firma_belirsiz")


def test_uneven_coverage_blocks_rise():
    prev = [rec(i, 7.5, source="x") for i in range(2)] + [rec(10 + i, 8.5 + i, source="eksi") for i in range(2)]
    cur = [rec(100 + i, 0.5 + (i % 6), source="x" if i % 2 else "eksi") for i in range(12)]
    g = _group(analyze(prev + cur, ASOF))
    assert g.clean_score > 1
    assert g.status == "dogrulanamadi"
    assert any("kapsama" in m for m in g.missing)


def test_balance_sampled_caps_x_per_query_day():
    from trend.analysis.signal import balance_sampled
    xs = [rec(i, 1.2, source="x") for i in range(30)]
    for r in xs:
        r.query = "kargom"
    es = [rec(100 + i, 1.2, source="eksi") for i in range(30)]
    kept, dropped = balance_sampled(xs + es, 25)
    assert dropped == 5 and len(kept) == 55
    assert kept == balance_sampled(list(reversed(xs + es)), 25)[0] or \
        sorted(r.id for r in kept) == sorted(r.id for r in balance_sampled(list(reversed(xs + es)), 25)[0])


def test_query_present_only_in_current_period_is_excluded():
    from trend.analysis.signal import drop_unbalanced_queries
    full = [rec(i, 0.5 + i) for i in range(13)]
    for r in full:
        r.query = "kargom"
    late = [rec(100 + i, 0.5 + i % 2, text=f"kargo gecikti {i} farklı {i*3}") for i in range(10)]
    for r in late:
        r.query = "kargo gecikti"
    kept, excluded = drop_unbalanced_queries(full + late, ASOF)
    assert "x:kargo gecikti" in excluded and "x:kargom" not in excluded
    assert len(kept) == 13


def test_kolay_gelsin_greeting_is_not_the_carrier():
    from trend.analysis.grouping import assign_brand
    assert assign_brand(rec(1, 1, text="Kolay gelsin herkese, sipariş için DM, PTT kargo ile gönderiyorum")) == "ptt"
    assert assign_brand(rec(2, 1, text="Kolay gelsin kargo 12 gündür paketimi teslim edemedi")) == "kolay_gelsin"


def test_window_parameter_changes_periods():
    rs = [rec(1, 2), rec(2, 10), rec(3, 20), rec(4, 25)]
    cur7, prev7, _, _ = split_periods(rs, ASOF)
    cur14, prev14, _, _ = split_periods(rs, ASOF, window=14)
    assert (len(cur7), len(prev7)) == (1, 1)
    assert (len(cur14), len(prev14)) == (2, 2)
    res = analyze(rs, ASOF, window=14)
    assert res["window_days"] == 14
    assert res["periods"]["previous"][0] == (ASOF - timedelta(days=28)).isoformat()


def test_min_sources_override():
    prev = [rec(i, 9 + i % 4, source="eksi") for i in range(2)]
    cur = [rec(100 + i, 0.5 + (i % 5), source="eksi") for i in range(10)]
    assert _group(analyze(prev + cur, ASOF)).status == "dogrulanamadi"
    assert _group(analyze(prev + cur, ASOF, min_sources=1)).status == "yukselis_adayi"


def test_record_counts_under_every_matching_theme():
    from trend.analysis.grouping import assign_themes
    text = "kargom 3 gündür bekliyor, canlı destek yardımcı olmadı"
    themes = assign_themes(text)
    assert "gecikme" in themes and "musteri_hizmetleri" in themes
    assert assign_themes("zaman zaman kargo kullanırım") == ["diger"]


def test_theme_word_end_avoids_place_names():
    from trend.analysis.grouping import assign_themes
    assert "hasar_kayip" not in assign_themes("kargom gelene kadar Kırıkkale'ye kış geldi")
    assert "hasar_kayip" in assign_themes("bardaklar kırık geldi")
