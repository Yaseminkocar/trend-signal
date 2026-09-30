from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import dotenv_values

from trend import config
from trend.cli import main as cli_main
from trend.pipeline import Options, run_analysis
from trend.report import STATUS_TR, write
from trend.topics import _slug, init_topic, keywords_from_label

ICON = Path(__file__).resolve().parent / "assets" / "icon.png"
SOURCES = {"eksi": "Ekşi Sözlük", "x": "X (Twitter)", "instagram": "Instagram", "tiktok": "TikTok"}
SOURCE_COLORS = {"eksi": "#2a78d6", "x": "#eb6834", "instagram": "#1baf7a", "tiktok": "#eda100"}
NEEDS_LOGIN = {"x": ("X_AUTH_TOKEN", "X_CT0"), "instagram": ("IG_SESSIONID",)}
CONFIDENCE = {"yuksek": "yüksek", "orta": "orta", "dusuk": "düşük", "-": "-"}
STATUS_PILL = {"yukselis_adayi": ("pill-ok", "Yükseliş adayı"), "dogrulanamadi": ("pill-warn", "Doğrulanamadı"),
               "yukselis_yok": ("pill-none", "Yükseliş yok")}
DIMENSION = {"tema": "Tema", "firma": "Firma"}

CSS = """
<style>
.block-container {padding-top: 2.2rem; max-width: 1200px;}
.hero {padding: 1.4rem 1.6rem; border-radius: 16px; margin-bottom: 1.2rem;
       background: linear-gradient(135deg, rgba(42,120,214,.16), rgba(27,175,122,.10));
       border: 1px solid rgba(42,120,214,.25);}
.hero h1 {font-size: 2rem; margin: 0 0 .3rem 0; padding: 0;}
.hero p {margin: 0; opacity: .8; font-size: .95rem;}
.pill {display: inline-block; padding: .15rem .6rem; border-radius: 999px; font-size: .78rem;
       font-weight: 600; letter-spacing: .01em; vertical-align: middle;}
.pill-ok {background: rgba(27,175,122,.18); color: #12925f; border: 1px solid rgba(27,175,122,.45);}
.pill-warn {background: rgba(237,161,0,.16); color: #b57a00; border: 1px solid rgba(237,161,0,.45);}
.pill-none {background: rgba(128,128,128,.14); color: inherit; border: 1px solid rgba(128,128,128,.35);}
.pill-miss {background: rgba(232,76,61,.14); color: #d0402f; border: 1px solid rgba(232,76,61,.4);}
.cand-title {font-size: 1.15rem; font-weight: 700; margin-right: .5rem;}
.cand-sub {opacity: .75; font-size: .88rem; margin-top: .2rem;}
.check {font-size: .9rem; margin: .15rem 0;}
div[data-testid="stMetric"] {border: 1px solid rgba(128,128,128,.25); border-radius: 12px; padding: .7rem 1rem;}
section[data-testid="stSidebar"] h2 {font-size: 1rem; margin-top: .6rem;}
@media (prefers-color-scheme: dark) {
  .pill-ok {color: #4cd6a0;}
  .pill-warn {color: #f2b53a;}
  .pill-miss {color: #ff8a7a;}
}
</style>
"""


class LiveLog(io.StringIO):
    def __init__(self, box):
        super().__init__()
        self.box = box

    def write(self, s: str) -> int:
        sys.__stdout__.write(s)
        sys.__stdout__.flush()
        n = super().write(s)
        lines = self.getvalue().splitlines()[-15:]
        self.box.code("\n".join(lines) or " ", language=None)
        return n


def missing_login() -> set[str]:
    env = dotenv_values(config.ROOT / ".env")
    return {src for src, keys in NEEDS_LOGIN.items() if not all(env.get(k) for k in keys)}


def last_day(name: str) -> date:
    from trend import store
    path = config.ROOT / "data" / name / "records.jsonl"
    today = date.today()
    if not name or not path.exists():
        return today
    days = [r.published_dt.astimezone(config.TR_TZ).date() for r in store.load(path) if r.published_at]
    return min(max(days), today) if days else today


def topic_name(label: str) -> str:
    text = label.strip()
    if text in config.available_topics():
        return text
    return _slug(text).replace("-", "_")


def ensure_topic(name: str, label: str, keywords: str, brands: str) -> str:
    import json
    kw = [k.strip() for k in keywords.split(",") if k.strip()]
    br = [b.strip() for b in brands.split(",") if b.strip()]
    path = config.TOPICS_DIR / f"{name}.json"
    if not path.exists():
        init_topic(name, label, kw or keywords_from_label(label), br)
        return "created"
    current = json.loads(path.read_text(encoding="utf-8"))
    if current.get("generated") and (kw or br):
        new_kw = kw or current.get("relevance_words", [])
        if new_kw != current.get("relevance_words") or (br and br != current.get("brand_labels")):
            init_topic(name, current.get("label", label), new_kw, br or current.get("brand_labels", []), force=True)
            return "updated"
    return ""


def collect(name: str, sources: list[str], days: int, until: date, fast: bool) -> list[str]:
    done = []
    for src in sources:
        args = ["--topic", name, "collect", src, "--days", str(days), "--until", until.isoformat()]
        if fast and src == "x":
            args += ["--per-day", "10", "--profiles", "5", "--no-retry", "--pace", "0.5"]
        if fast and src == "eksi":
            args += ["--delay", "1.0", "--max-discovered", "10"]
        with st.status(f"{SOURCES[src]} toplanıyor...", expanded=True) as box:
            log = LiveLog(st.empty())
            try:
                with redirect_stdout(log):
                    cli_main(args)
                done.append(src)
                box.update(label=f"{SOURCES[src]} tamamlandı", state="complete", expanded=False)
            except (Exception, SystemExit) as e:
                log.write(f"\n{type(e).__name__}: {e}\n")
                box.update(label=f"{SOURCES[src]} atlandı: {e}", state="error", expanded=False)
    return done


def daily_frame(records, asof: datetime, window: int) -> pd.DataFrame:
    start = (asof - timedelta(days=2 * window)).date()
    rows = [(r.published_dt.astimezone(config.TR_TZ).date(), r.source) for r in records if r.published_at]
    df = pd.DataFrame(rows, columns=["gun", "kaynak"])
    df = df[(df["gun"] >= start) & (df["gun"] < asof.date())]
    if df.empty:
        return df
    table = df.groupby(["gun", "kaynak"]).size().unstack(fill_value=0)
    days = pd.date_range(start, asof.date() - timedelta(days=1)).date
    table = table.reindex(days, fill_value=0)
    table.index = pd.Index([d.strftime("%d.%m") for d in table.index], name="gün")
    table = table[[s for s in SOURCES if s in table.columns]]
    return table


def group_table(groups) -> pd.DataFrame:
    return pd.DataFrame([{
        "grup": pretty(g.group),
        "önceki": g.unique_previous,
        "son": g.unique_current,
        "temiz puan": round(g.clean_score, 2),
        "tekrar etkisi": round(g.duplicate_effect, 2),
        "yazar": g.authors_current,
        "gün": g.active_days_current,
        "kaynak": ", ".join(g.sources_current),
        "durum": STATUS_TR[g.status],
        "eksik kanıt": "; ".join(g.missing),
    } for g in groups])


def pill(status: str) -> str:
    cls, text = STATUS_PILL[status]
    return f'<span class="pill {cls}">{text}</span>'


def pretty(group: str) -> str:
    dim, _, value = group.partition(":")
    return f"{DIMENSION.get(dim, dim)} · {value.replace('_', ' ')}"


def show_candidate(g, window: int) -> None:
    with st.container(border=True):
        st.markdown(f'<span class="cand-title">{pretty(g.group)}</span>{pill(g.status)}'
                    f'<div class="cand-sub">güven: {CONFIDENCE.get(g.confidence, g.confidence)} · '
                    f'kaynak: {", ".join(SOURCES.get(s, s) for s in g.sources_current) or "-"}</div>',
                    unsafe_allow_html=True)
        c = st.columns(4)
        c[0].metric(f"Önceki {window} gün", g.unique_previous)
        c[1].metric(f"Son {window} gün", g.unique_current, delta=g.unique_current - g.unique_previous)
        c[2].metric("Temiz puan", f"{g.clean_score:+.2f}")
        c[3].metric("Yazar / gün", f"{g.authors_current} / {g.active_days_current}")
        left, right = st.columns(2)
        for i, chk in enumerate(g.checks):
            tag = '<span class="pill pill-ok">sağlandı</span>' if chk.passed else '<span class="pill pill-miss">eksik</span>'
            (left if i % 2 == 0 else right).markdown(f'<div class="check">{tag} {chk.detail}</div>',
                                                     unsafe_allow_html=True)
        if g.evidence:
            with st.expander(f"Kanıt ({len(g.evidence)})"):
                for e in g.evidence:
                    when = (e["published_at"] or "tarih yok")[:16].replace("T", " ")
                    text = e["text"][:160].replace("[", "(").replace("]", ")")
                    st.markdown(f"**{SOURCES.get(e['source'], e['source'])}** · {when} · [bağlantı]({e['url']})  \n{text}")


def show_result(out, window: int) -> None:
    result = out.result
    t = result["totals"]
    tumu = next(g for g in result["groups"] if g.group == "TUMU")
    groups = [g for g in result["groups"] if g.group != "TUMU"]
    candidates = [g for g in groups if g.status != "yukselis_yok"][:3]

    st.markdown(f"Genel durum: {pill(tumu.status)}", unsafe_allow_html=True)
    cols = st.columns(4)
    cols[0].metric("Analize giren kayıt", t["records"])
    cols[1].metric(f"Önceki {window} gün", t["previous"])
    cols[2].metric(f"Son {window} gün", t["current"], delta=t["current"] - t["previous"])
    cols[3].metric("Genel temiz puan", f"{tumu.clean_score:+.2f}")

    st.subheader("Aday sinyaller")
    if not candidates:
        st.info("Eşiği geçen grup yok: yükseliş bulunamadı. Bu da geçerli bir sonuç.")
    for g in candidates:
        show_candidate(g, window)

    st.subheader("Günlere göre içerik")
    daily = daily_frame(out.records, datetime.fromisoformat(result["asof"]), window)
    if daily.empty:
        st.caption("Seçilen dönemde tarihli kayıt yok.")
    else:
        st.caption(f"Soldaki {window} gün önceki dönem, sağdaki {window} gün son dönem.")
        colors = [SOURCE_COLORS[s] for s in daily.columns]
        st.bar_chart(daily.rename(columns=SOURCES), color=colors, x_label="gün", y_label="içerik sayısı")

    st.subheader("Tüm gruplar")
    only_active = st.toggle("Yalnız yükselişi olan grupları göster", value=False)
    shown = [g for g in groups if g.status != "yukselis_yok"] if only_active else groups
    st.dataframe(group_table(shown), hide_index=True, width="stretch")

    with st.expander("Uygulanan filtreler ve uyarılar"):
        for n in out.notes or ["Uyarı yok."]:
            st.markdown(f"- {n}")
        cov = result.get("coverage", {})
        if cov:
            st.markdown("Gün kapsaması (önceki / son): " +
                        ", ".join(f"{k} {v['previous_days']}/{v['current_days']}" for k, v in sorted(cov.items())))

    if out.verdicts:
        with st.expander("Hesap tahminleri (X)"):
            st.dataframe(pd.DataFrame([{"hesap (maskeli)": v.author, "puan": v.score, "etiket": v.label,
                                        "gerekçe": "; ".join(v.reasons)} for v in out.verdicts])
                         .sort_values("puan", ascending=False), hide_index=True, width="stretch")

    md = write(result, out.verdicts, config.OUTPUT_DIR)
    c1, c2 = st.columns(2)
    c1.download_button("Raporu indir (.md)", md.read_text(encoding="utf-8"), file_name=f"{config.TOPIC}_sinyal.md")
    c2.download_button("Veriyi indir (.json)", (md.parent / "signals.json").read_text(encoding="utf-8"),
                       file_name=f"{config.TOPIC}_sinyal.json")


def main() -> None:
    st.set_page_config(page_title="Trend Intelligence", page_icon=str(ICON), layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown('<div class="hero"><h1>Erken trend sinyali</h1><p>Bir konu girin, kaynakları ve dönemi seçin. '
                'Son dönem önceki dönemle kıyaslanır; kopyalar, ilanlar ve bot olası hesaplar ayıklanır, '
                'kanıtı yetersiz sonuç "doğrulanamadı" diye işaretlenir.</p></div>', unsafe_allow_html=True)

    label = st.text_input("Konu", value="", placeholder="ör. telefon fiyatları, elektrikli araç, kahve")
    st.caption("Kayıtlı konular: " + ", ".join(config.available_topics()) +
               ". Repodaki örnek veriyi görmek için 'kargo' yazıp 'Kayıtlı veriyle analiz et' düğmesine basın.")
    with st.expander("Yeni konu için anahtar kelimeler ve markalar (isteğe bağlı)"):
        keywords = st.text_input("Anahtar kelimeler (virgülle)", placeholder="ör. filtre kahve, kahve fiyatı")
        brands = st.text_input("Markalar (virgülle)", placeholder="ör. Starbucks, Kahve Dünyası")

    with st.sidebar:
        st.header("Kaynaklar")
        no_login = missing_login()
        picked = []
        for src, name in SOURCES.items():
            if st.checkbox(name, value=src in ("eksi", "x")):
                picked.append(src)
            if src in no_login:
                st.caption(f"{name} için .env dosyasında giriş bilgisi yok; toplama atlanır.")

        st.header("Dönem")
        window = st.radio("Karşılaştırma", [7, 14, 21], horizontal=True,
                          format_func=lambda d: f"{d} gün", help="Son N gün, önceki N günle kıyaslanır.")
        until = st.date_input("Son gün", value=last_day(topic_name(label) if label.strip() else ""),
                              max_value=date.today(), format="DD.MM.YYYY",
                              help="Kayıtlı veri varsa varsayılan, verideki son gündür.")

        st.header("Filtreler")
        relevance = st.checkbox("Konu dışı içeriği çıkar", value=True)
        ads = st.checkbox("İlan ve kurumsal paylaşımları çıkar (Instagram, TikTok)", value=True)
        bots = st.checkbox("Bot olası hesapları çıkar (X)", value=True)
        min_sources = st.number_input("Yükseliş için en az kaynak", 1, 4, config.MIN_SOURCES)

        st.header("Toplama")
        fast = st.checkbox("Hızlı toplama", value=True,
                           help="Ekşi'de en fazla 10 ek başlık, X'te günde en fazla 10 gönderi ve 5 hesap profili alınır, "
                                "bekleme süreleri kısalır ve boş dönen gün tekrar denenmez. Kapatılırsa sonuç daha sağlam "
                                "ama X toplaması 15-30 dakika sürebilir.")

    name = topic_name(label) if label.strip() else ""
    asof = datetime.combine(until + timedelta(days=1), time(0), tzinfo=config.TR_TZ)
    c1, c2 = st.columns(2)
    run_collect = c1.button("Veri topla ve analiz et", type="primary", width="stretch",
                            disabled=not (name and picked))
    run_only = c2.button("Kayıtlı veriyle analiz et", width="stretch",
                         disabled=not (name and picked))
    c2.caption("İnternet gerekmez.")
    if name:
        known = name in config.available_topics()
        st.caption(f"Konu: **{name}**" + (" (kayıtlı)" if known else " (yeni; ilk toplamada oluşturulacak)"))

    if not (run_collect or run_only):
        return
    if run_only and name not in config.available_topics():
        st.error(f"'{label}' için kayıtlı veri yok. Önce 'Veri topla ve analiz et' ile toplayın.")
        return
    change = ensure_topic(name, label.strip(), keywords, brands)
    if change == "created":
        st.info(f"Yeni konu oluşturuldu: topics/{name}.json. Sorgular ve temalar bu dosyadan düzenlenebilir.")
    elif change == "updated":
        st.info(f"topics/{name}.json yeni anahtar kelime ve markalarla güncellendi.")
    config.use_topic(name)

    sources = picked
    if run_collect:
        if "x" in picked:
            st.caption("X toplaması hızlı modda birkaç dakika, tam modda 15-30 dakika sürebilir. "
                       "Sayfadaki bir ayarı değiştirmek toplamayı durdurur.")
        sources = collect(name, picked, 2 * window, until, fast)
        if not sources:
            st.error("Hiçbir kaynaktan veri toplanamadı.")
            return
    if len(sources) < min_sources:
        st.warning(f"Yalnız {len(sources)} kaynak seçili; sonuç en fazla 'doğrulanamadı' olabilir.")

    try:
        out = run_analysis(Options(sources=tuple(sources), asof=asof, window=window, relevance_filter=relevance,
                                   ad_filter=ads, bot_filter=bots, min_sources=int(min_sources)))
    except SystemExit as e:
        st.error(str(e))
        return
    st.divider()
    st.subheader(f"{config.TOPIC_LABEL}")
    st.caption(f"Son dönem {asof - timedelta(days=window):%d.%m} - {until:%d.%m.%Y}, önceki {window} günle kıyaslandı.")
    show_result(out, window)


main()
