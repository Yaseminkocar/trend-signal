from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from datetime import date, datetime, time, timedelta

import pandas as pd
import streamlit as st
from dotenv import dotenv_values

from trend import config
from trend.cli import main as cli_main
from trend.pipeline import Options, run_analysis
from trend.report import STATUS_TR, write
from trend.topics import _slug, init_topic, keywords_from_label

SOURCES = {"eksi": "Ekşi Sözlük", "x": "X (Twitter)", "instagram": "Instagram", "tiktok": "TikTok"}
SOURCE_COLORS = {"eksi": "#2a78d6", "x": "#eb6834", "instagram": "#1baf7a", "tiktok": "#eda100"}
NEEDS_LOGIN = {"x": ("X_AUTH_TOKEN", "X_CT0"), "instagram": ("IG_SESSIONID",)}
CONFIDENCE = {"yuksek": "yüksek", "orta": "orta", "dusuk": "düşük", "-": "-"}


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


def ensure_topic(name: str, label: str, keywords: str, brands: str) -> bool:
    if name in config.available_topics():
        return False
    kw = [k.strip() for k in keywords.split(",") if k.strip()] or keywords_from_label(label)
    init_topic(name, label, kw, [b.strip() for b in brands.split(",") if b.strip()])
    return True


def collect(name: str, sources: list[str], days: int, until: date, fast: bool) -> list[str]:
    done = []
    for src in sources:
        args = ["--topic", name, "collect", src, "--days", str(days), "--until", until.isoformat()]
        if src == "x" and fast:
            args += ["--per-day", "10", "--profiles", "10", "--no-retry"]
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
        "grup": g.group,
        "önceki": g.unique_previous,
        "son": g.unique_current,
        "temiz puan": round(g.clean_score, 2),
        "tekrar etkisi": round(g.duplicate_effect, 2),
        "yazar": g.authors_current,
        "gün": g.active_days_current,
        "kaynak": ", ".join(g.sources_current),
        "durum": STATUS_TR[g.status],
    } for g in groups])


def show_candidate(g, window: int) -> None:
    title = f"{g.group}: {STATUS_TR[g.status]}"
    body = (f"Tekil içerik: önceki {window} gün **{g.unique_previous}**, son {window} gün **{g.unique_current}** "
            f"(temiz puan {g.clean_score:+.2f}, güven: {CONFIDENCE.get(g.confidence, g.confidence)})")
    if g.status == "yukselis_adayi":
        st.success(f"**{title}**  \n{body}")
    else:
        st.warning(f"**{title}**  \n{body}")
    for c in g.checks:
        st.markdown(f"- {'Sağlandı' if c.passed else '**Eksik**'}: {c.detail}")
    if g.evidence:
        st.markdown("Kanıt:")
        for e in g.evidence:
            when = (e["published_at"] or "tarih yok")[:16].replace("T", " ")
            text = e["text"][:120].replace("[", "(").replace("]", ")")
            st.markdown(f"- **{SOURCES.get(e['source'], e['source'])}**, {when}: [{e['url']}]({e['url']})  \n  {text}")


def show_result(out, window: int) -> None:
    result = out.result
    t = result["totals"]
    tumu = next(g for g in result["groups"] if g.group == "TUMU")
    groups = [g for g in result["groups"] if g.group != "TUMU"]
    candidates = [g for g in groups if g.status != "yukselis_yok"][:3]

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
    st.set_page_config(page_title="Trend Sinyali", layout="wide")
    st.title("Erken trend sinyali")
    st.caption("Bir konu girin, kaynakları ve dönemi seçin. Son dönem önceki dönemle kıyaslanır; "
               "kopyalar, ilanlar ve bot olası hesaplar ayıklanır, kanıtı yetersiz sonuç 'doğrulanamadı' diye işaretlenir.")

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
        fast = st.checkbox("Hızlı toplama (X)", value=True,
                           help="X'te günde en fazla 10 gönderi ve 10 hesap profili alınır; boş dönen gün için "
                                "beklenip tekrar denenmez. Kapatılırsa sonuç daha sağlam ama toplama 15-30 dakika sürebilir.")

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
    if ensure_topic(name, label.strip(), keywords, brands):
        st.info(f"Yeni konu oluşturuldu: topics/{name}.json. Sorgular ve temalar bu dosyadan düzenlenebilir.")
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
    st.header(f"{config.TOPIC_LABEL}: {asof - timedelta(days=window):%d.%m} - {until:%d.%m.%Y} "
              f"(önceki {window} günle kıyas)")
    show_result(out, window)


main()
