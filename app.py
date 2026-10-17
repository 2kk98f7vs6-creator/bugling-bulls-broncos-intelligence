"""Bugling Bulls v0.2 — read-only, shareable Broncos scouting dashboard.

Important: no write forms, notebook data, accounts, live downloads or secret files.
The same published, validated dataset is read by every visitor. Each visitor's
filters are held in their own Streamlit session only.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from analysis_engine import (
    data_coverage,
    derive,
    group_performance,
    metric_summary,
    trend_signals,
    weekly_report,
)

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
ASSETS = ROOT / "assets"
PLAYFILE = DATA / "broncos_plays.csv"
NGSFILE = DATA / "bo_nix_ngs_weekly.csv"
STATUSFILE = DATA / "import_status.json"
WATERMARK_FILE = ASSETS / "broncos_watermark.png"

st.set_page_config(
    page_title="Bugling Bulls | Broncos Intelligence",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded",
)


def watermark_css() -> str:
    if WATERMARK_FILE.exists():
        try:
            encoded = base64.b64encode(WATERMARK_FILE.read_bytes()).decode("utf-8")
            background_image = f"url('data:image/png;base64,{encoded}')"
        except OSError:
            background_image = "none"
    else:
        background_image = "none"

    return f"""
    <style>
    :root {{
        --broncos-navy: #0A2342;
        --broncos-navy-2: #13315C;
        --broncos-orange: #FB4F14;
        --sunset-pink: #FF7AA2;
        --sunset-soft: #FFC1B6;
        --panel: rgba(255,255,255,0.08);
        --panel-2: rgba(255,255,255,0.12);
        --border: rgba(255,255,255,0.15);
        --text-main: #F6F8FB;
        --text-soft: #D7E2F0;
    }}

    html, body, [class*="css"] {{
        color: var(--text-main);
    }}

    .stApp {{
        background:
            radial-gradient(circle at top right, rgba(251,79,20,0.22), transparent 26%),
            radial-gradient(circle at bottom left, rgba(255,122,162,0.14), transparent 28%),
            linear-gradient(180deg, #0A2342 0%, #10294C 46%, #0A2342 100%);
        color: var(--text-main);
    }}

    .stApp::before {{
        content: "";
        position: fixed;
        inset: 0;
        background-image: {background_image};
        background-repeat: no-repeat;
        background-position: center 52%;
        background-size: min(52vw, 620px);
        opacity: 0.06;
        pointer-events: none;
        z-index: 0;
        filter: grayscale(1) brightness(2.2);
    }}

    [data-testid="stAppViewContainer"] > .main {{
        position: relative;
        z-index: 1;
    }}

    .block-container {{
        max-width: 1510px;
        padding-top: 1.35rem;
        padding-bottom: 2.2rem;
    }}

    h1, h2, h3 {{
        letter-spacing: -0.026em;
        color: var(--text-main) !important;
    }}

    p, li, label, .stMarkdown, .stCaption, .st-emotion-cache-10trblm,
    .st-emotion-cache-16idsys p, .stAlert, .stInfo, .stWarning {{
        color: var(--text-soft) !important;
    }}

    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #FB4F14 0%, #FF7AA2 100%) !important;
        border-right: 1px solid rgba(255,255,255,0.18);
    }}

    [data-testid="stSidebar"] * {{
        color: #FFFFFF !important;
    }}

    [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div,
    [data-testid="stSidebar"] .stMultiSelect div[data-baseweb="select"] > div,
    [data-testid="stSidebar"] .stRadio > div,
    [data-testid="stSidebar"] .stTextInput input {{
        background: rgba(255,255,255,0.18) !important;
        border: 1px solid rgba(255,255,255,0.28) !important;
        border-radius: 12px !important;
        color: #FFFFFF !important;
    }}

    div[data-baseweb="popover"] * {{
        color: #0A2342 !important;
    }}

    [data-testid="stMetric"], .stMetric {{
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 14px;
        background: linear-gradient(180deg, rgba(255,255,255,0.10), rgba(255,255,255,0.06));
        backdrop-filter: blur(6px);
        box-shadow: 0 8px 24px rgba(3, 15, 30, 0.16);
    }}

    [data-testid="stDataFrame"], [data-testid="stTable"], .st-emotion-cache-1wmy9hl,
    [data-testid="stExpander"], [data-testid="stAlert"], [data-testid="stVerticalBlockBorderWrapper"] {{
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid var(--border) !important;
        border-radius: 16px !important;
        backdrop-filter: blur(6px);
    }}

    [data-baseweb="tab-list"] {{
        gap: .25rem;
    }}

    button[data-baseweb="tab"] {{
        background: rgba(255,255,255,0.08) !important;
        border-radius: 12px 12px 0 0 !important;
        color: var(--text-soft) !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        border-bottom: none !important;
        padding-inline: .95rem !important;
    }}

    button[data-baseweb="tab"][aria-selected="true"] {{
        background: rgba(255,255,255,0.14) !important;
        color: #FFFFFF !important;
    }}

    .stDownloadButton button, .stButton button {{
        background: linear-gradient(135deg, #FB4F14 0%, #FF7AA2 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 999px !important;
        font-weight: 600 !important;
    }}

    .stDownloadButton button:hover, .stButton button:hover {{
        filter: brightness(1.06);
    }}

    .stCodeBlock, code {{
        border-radius: 12px !important;
    }}

    a {{
        color: #FFC86C !important;
    }}
    </style>
    """


st.markdown(watermark_css(), unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_play_data(path: str, mtime_ns: int) -> pd.DataFrame:
    raw = pd.read_csv(path, low_memory=False)
    return derive(raw)


@st.cache_data(show_spinner=False)
def load_ngs_data(path: str, mtime_ns: int) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def pretty(value, percentage: bool = False, signed: bool = False):
    if value is None or pd.isna(value):
        return "N/A"
    if percentage:
        return f"{value:.1%}"
    return f"{value:+.3f}" if signed else f"{value:.3f}"


def numeric_metrics(data: pd.DataFrame, side: str):
    result = metric_summary(data, side)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Charted scrimmage plays", f'{result["plays"]:,}')
    c2.metric("EPA/play" if side == "Offense" else "EPA allowed/play", pretty(result["epa"], signed=True))
    c3.metric("Success rate" if side == "Offense" else "Opp. success rate", pretty(result["success"], percentage=True))
    c4.metric("Explosive rate" if side == "Offense" else "Explosives allowed", pretty(result["explosive"], percentage=True))
    c5.metric("Dropback rate" if side == "Offense" else "Opp. dropback rate", pretty(result["pass_rate"], percentage=True))


def group_table(data: pd.DataFrame, side: str, field: str, label: str, min_n: int = 1, show_chart: bool = True):
    st.markdown(f"**{label}**")
    groups = group_performance(data, field, side, min_plays=min_n)
    if groups.empty:
        st.info("No charted plays for this breakdown. Change your filters or select a historical season.")
        return groups
    display = groups.copy()
    for column in ["EPA/play", "Success %", "Explosive %", "Pass rate %"]:
        display[column] = display[column].round(3 if column == "EPA/play" else 1)
    st.dataframe(display, hide_index=True, use_container_width=True)
    if show_chart and len(groups) > 1:
        bar = px.bar(
            groups.head(14),
            x=field,
            y="EPA/play",
            hover_data=["Plays", "Success %", "Sample"],
            title="Observed EPA/play by group (not adjusted for opposition)",
        )
        bar.add_hline(y=0, line_color="gray", line_dash="dot")
        bar.update_layout(
            margin=dict(l=10, r=10, t=48, b=10),
            height=330,
            xaxis_title=None,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(255,255,255,0.03)",
            font_color="#F6F8FB",
        )
        st.plotly_chart(bar, use_container_width=True)
    return groups


def evidence(data: pd.DataFrame, key: str, caption="Supporting plays"):
    st.markdown(f"#### {caption}")
    cols = [c for c in [
        "season", "week", "game_id", "play_id", "side", "opponent", "qtr", "time",
        "down", "ydstogo", "play_call", "yards_gained", "epa", "success",
        "personnel_code", "formation_name", "defensive_package", "qb_alignment",
        "is_motion", "is_play_action", "is_screen_pass", "n_pass_rushers",
        "defense_man_zone_type", "defense_coverage_type", "desc",
    ] if c in data]
    if data.empty:
        st.info("There are no plays matching this question and these filters.")
        return
    st.caption(f"{len(data):,} underlying plays; missing charting fields are left blank.")
    st.dataframe(data[cols].head(1500), use_container_width=True, hide_index=True, height=345)
    st.download_button(
        "Download all matching plays (.csv)",
        data.to_csv(index=False).encode("utf-8"),
        file_name=f"bugling_bulls_{key}.csv",
        mime="text/csv",
        key=f"dl_{key}",
    )


def side_filter(data, side):
    return data.loc[data.side.eq(side)].copy()


def game_label(game, df):
    r = df.loc[df.game_id.eq(game)].iloc[0]
    return f"{r.season} · W{r.week} · vs {r.opponent} ({game})"


def snapshot_info():
    if not STATUSFILE.exists():
        return
    try:
        x = json.loads(STATUSFILE.read_text(encoding="utf-8"))
        st.caption(f'Public data snapshot: {x.get("updated_utc", "unknown")} UTC · {x.get("games", "?")} games · {x.get("plays", "?")} plays')
        errors = x.get("source_errors") or []
        if errors:
            with st.expander("Import caveats"):
                for err in errors:
                    st.write(err)
    except (ValueError, OSError):
        st.caption("Snapshot metadata is unavailable.")


st.title("🏈 Bugling Bulls | Broncos Intelligence Center")
st.caption("FAN BETA v0.2  •  Play-calling evidence, personnel matchups, Denver offense & defense")

if not PLAYFILE.exists():
    st.warning("This deployment has no published Broncos data yet. It will not invent any sample statistics.")
    st.markdown("**For the owner:** populate the `data/` snapshot locally, or run **Actions → Refresh public Broncos data → Run workflow** in your GitHub repository. Commit the generated public data files before sharing the site.")
    st.code("python data_pipeline.py --seasons 2024 2025 2026", language="bash")
    st.stop()
try:
    df = load_play_data(str(PLAYFILE), PLAYFILE.stat().st_mtime_ns)
except Exception as exc:
    st.error(f"Could not load the published data: {exc}")
    st.stop()
if df.empty:
    st.warning("The data file contains no Broncos scrimmage plays.")
    st.stop()

all_seasons = sorted(pd.to_numeric(df.season, errors="coerce").dropna().astype(int).unique(), reverse=True)
all_games = (
    df[["season", "week", "game_id"]]
    .drop_duplicates()
    .sort_values(["season", "week", "game_id"], ascending=False)
)
all_game_ids = all_games.game_id.tolist()
labels = {g: game_label(g, df) for g in all_game_ids}

st.sidebar.header("Scouting filters")
season_option = st.sidebar.selectbox("Season", ["All seasons"] + all_seasons, index=1 if all_seasons else 0)
season_df = df if season_option == "All seasons" else df.loc[df.season.eq(int(season_option))]
season_games = [g for g in all_game_ids if g in set(season_df.game_id)]
game_choice = st.sidebar.selectbox(
    "Game",
    ["All games"] + season_games,
    index=1 if season_games else 0,
    format_func=lambda g: "All games in selected season(s)" if g == "All games" else labels[g],
)
base = season_df if game_choice == "All games" else season_df.loc[season_df.game_id.eq(game_choice)]
side_choice = st.sidebar.radio("View", ["Both sides", "Offense", "Defense"], horizontal=True)
downs = st.sidebar.multiselect("Down", [1, 2, 3, 4], default=[1, 2, 3, 4])
distance_bands = ["1–2", "3–6", "7–10", "11+"]
distance_choice = st.sidebar.multiselect("Yards to go", distance_bands, default=distance_bands)
context = base.loc[base.down.isin(downs) & base.distance_band.astype(str).isin(distance_choice)].copy()
if side_choice != "Both sides":
    context = context.loc[context.side.eq(side_choice)]
st.sidebar.caption("Filters apply to explorers. Weekly scorecards always use the complete selected game, avoiding misleading partial-game headlines.")

snapshot_info()
st.info("EPA is the offense’s expected points added. **Positive favors Denver on offense; negative EPA allowed favors Denver on defense.** Results are observed correlations, not proof of a good or bad coaching decision.", icon="ℹ️")

pages = st.tabs([
    "Weekly Intelligence", "Ask Bugling Bulls", "Personnel & Formations",
    "Offense", "Defense", "Bo Nix NGS", "Play Evidence", "Data Quality",
])

with pages[0]:
    st.subheader("Weekly game intelligence")
    if game_choice == "All games":
        st.caption("Choose one game in the sidebar to produce the complete postgame scorecard and rolling trend flags.")
    else:
        st.caption("This game report deliberately ignores the down/distance sidebar filters.")
    complete = base.copy()
    st.markdown("### Denver offense")
    numeric_metrics(complete, "Offense")
    st.markdown("### Denver defense")
    numeric_metrics(complete, "Defense")
    if game_choice != "All games":
        st.markdown("#### Changes worth reviewing")
        alerts = trend_signals(df, game_choice)
        if not alerts:
            st.info("No changes met the predefined descriptive thresholds, or fewer than two prior games are available.")
        else:
            for a in alerts:
                st.markdown(f'**{a["title"]}** — {a["detail"]}  \n*{a["n"]} plays in current sample; not opponent-adjusted.*')
        report = weekly_report(df, game_choice)
        st.download_button(
            "Download game report (.md)",
            data=report,
            file_name=f"Broncos_{game_choice}_weekly_report.md",
            mime="text/markdown",
        )
        with st.expander("Read the full deterministic report"):
            st.markdown(report)
    st.markdown("#### The 2024–2026 story, game by game")
    trend = (
        df.groupby(["game_id", "season", "week", "side"], as_index=False)
        .agg(epa=("epa", "mean"), plays=("play_id", "size"))
    )
    trend["Match"] = trend.season.astype(str) + " W" + trend.week.astype(str)
    for which in ["Offense", "Defense"]:
        chart = trend.loc[trend.side.eq(which)].sort_values(["season", "week", "game_id"])
        if not chart.empty:
            fig = px.line(
                chart,
                x="Match",
                y="epa",
                markers=True,
                title=f'{which}: ' + ("EPA/play" if which == "Offense" else "EPA allowed/play"),
                hover_data=["plays", "game_id"],
            )
            fig.add_hline(y=0, line_color="gray", line_dash="dot")
            fig.update_layout(
                height=270,
                margin=dict(l=10, r=10, t=45, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(255,255,255,0.03)",
                font_color="#F6F8FB",
            )
            st.plotly_chart(fig, use_container_width=True)

with pages[1]:
    st.subheader("Ask Bugling Bulls")
    st.caption("Reliable predefined football questions. Open-ended AI answers and automated expert film adjudication are not implemented yet.")
    questions = [
        "Why has Denver struggled on third down?",
        "How do 11 and 12 personnel compare for Denver?",
        "Are formations signaling run or pass?",
        "How does Denver attack opposing defensive personnel?",
        "How effective are Joseph’s different pass-rush counts?",
        "How do Webb and Payton play-calling periods compare?",
        "Are motion, play-action and screens productive?",
    ]
    q = st.selectbox("Choose an investigative question", questions)
    subset = context.copy()
    if q == questions[0]:
        subset = subset.loc[subset.side.eq("Offense") & subset.down.eq(3)]
        group_table(subset, "Offense", "distance_band", "Third-down EPA by distance")
        st.caption("Official third-down totals may differ because penalty-only plays are not included.")
    elif q == questions[1]:
        subset = subset.loc[subset.side.eq("Offense") & subset.personnel_code.isin(["11", "12"])]
        group_table(subset, "Offense", "personnel_code", "Denver: 11 vs 12 personnel")
        group_table(subset, "Offense", "play_call", "Run versus dropback within the selected personnel")
    elif q == questions[2]:
        subset = subset.loc[subset.side.eq("Offense")]
        group_table(subset, "Offense", "formation_name", "Reported formation", show_chart=False)
        group_table(subset, "Offense", "qb_alignment", "Quarterback alignment (weekly FTN)", show_chart=False)
        st.caption("Full receiver arrangement (trips, bunch) is NOT inferred from generic Shotgun labels.")
    elif q == questions[3]:
        subset = subset.loc[subset.side.eq("Offense")]
        group_table(subset, "Offense", "defensive_package", "Opponent defensive personnel against Denver")
    elif q == questions[4]:
        subset = subset.loc[subset.side.eq("Defense") & subset.play_call.eq("Pass / dropback")]
        group_table(subset, "Defense", "n_pass_rushers", "Rushers on opposing dropbacks")
        st.caption("Different rush counts are called in different situations. EPA differences do not prove causality.")
    elif q == questions[5]:
        subset = subset.loc[subset.side.eq("Offense") & subset.season.eq(2026)]
        group_table(subset, "Offense", "play_caller", "2026 primary offensive play-caller period")
        st.caption("Webb W1–4 vs Payton W5 onward, based on public reporting; opponents and circumstances differ.")
    else:
        subset = subset.loc[subset.side.eq("Offense")]
        c1, c2, c3 = st.columns(3)
        with c1:
            group_table(subset, "Offense", "is_motion", "Motion charting", show_chart=False)
        with c2:
            group_table(subset, "Offense", "is_play_action", "Play-action charting", show_chart=False)
        with c3:
            group_table(subset, "Offense", "is_screen_pass", "Screen charting", show_chart=False)
    evidence(subset, "ask", caption="Plays behind this answer")

with pages[2]:
    st.subheader("Personnel × formation × defensive matchup")
    st.caption("Historical participation charting supports detailed personnel analysis; the latest season may have no released personnel yet. Blank means unavailable, not “zero usage.”")
    left, right = st.columns(2)
    with left:
        group_table(context, "Offense", "personnel_code", "Denver offensive personnel")
        group_table(context, "Offense", "formation_name", "Denver offensive formation")
    with right:
        group_table(context, "Offense", "defensive_package", "Opponent defensive personnel")
        group_table(context, "Defense", "defensive_package", "Denver defensive personnel")
    st.markdown("#### Cross-match: Broncos personnel vs opponent package")
    offense = side_filter(context, "Offense")
    if {"personnel_code", "defensive_package"}.issubset(offense.columns):
        offense["matchup"] = offense.personnel_code.fillna("") + " vs " + offense.defensive_package.fillna("")
        offense.loc[offense.personnel_code.isna() | offense.defensive_package.isna(), "matchup"] = pd.NA
        group_table(offense, "Offense", "matchup", "Charted personnel matchup", min_n=3)
    st.markdown("#### What did Denver face on defense?")
    group_table(context, "Defense", "personnel_code", "Opponent offensive personnel (Denver defending)", min_n=3)
    st.markdown("#### Weekly alignment proxy")
    group_table(context, "Offense", "qb_alignment", "Under center / shotgun / pistol")
    st.caption("This release does not identify precise fronts, run-blocking families or Cover 1/3/4 without supporting charting or expert film.")

with pages[3]:
    st.subheader("Offensive decision analysis")
    offense = side_filter(context, "Offense")
    group_table(offense, "Offense", "down", "By down")
    a, b = st.columns(2)
    with a:
        group_table(offense, "Offense", "play_call", "Designed runs versus dropbacks")
    with b:
        group_table(offense, "Offense", "distance_band", "By distance")
    group_table(offense, "Offense", "play_caller", "By primary play-caller period")
    third = offense.loc[offense.down.eq(3)]
    if not third.empty:
        st.metric("Tracked third-down conversion", pretty(pd.to_numeric(third.converted, errors="coerce").mean(), percentage=True))

with pages[4]:
    st.subheader("Defensive decisions and pressures")
    defense = side_filter(context, "Defense")
    a, b = st.columns(2)
    with a:
        group_table(defense, "Defense", "down", "Opposing offense by down")
    with b:
        group_table(defense, "Defense", "play_call", "Run versus dropback allowed")
    pass_df = defense.loc[defense.play_call.eq("Pass / dropback")]
    a, b = st.columns(2)
    with a:
        group_table(pass_df, "Defense", "n_pass_rushers", "Charted pass-rusher count")
    with b:
        group_table(pass_df, "Defense", "n_blitzers", "Charted blitzer count")
    group_table(defense, "Defense", "defense_coverage_type", "Historical coverage family")
    st.caption("Coverage fields are sourced from historical participation only, when populated. No coverage is predicted from play descriptions.")

with pages[5]:
    st.subheader("Bo Nix — official NGS weekly aggregates")
    if not NGSFILE.exists():
        st.info("The NGS source has not been included in this public snapshot yet.")
    else:
        ngs = load_ngs_data(str(NGSFILE), NGSFILE.stat().st_mtime_ns)
        if season_option != "All seasons":
            ngs = ngs.loc[pd.to_numeric(ngs.season, errors="coerce").eq(int(season_option))]
        if game_choice != "All games":
            match = base.iloc[0]
            ngs = ngs.loc[
                pd.to_numeric(ngs.season, errors="coerce").eq(int(match.season))
                & pd.to_numeric(ngs.week, errors="coerce").eq(int(match.week))
            ]
        if ngs.empty:
            st.info("No Bo Nix weekly NGS records match this selection.")
        else:
            cols = [
                x for x in [
                    "season", "week", "attempts", "avg_time_to_throw", "avg_intended_air_yards",
                    "avg_air_yards_to_sticks", "completion_percentage",
                    "expected_completion_percentage", "completion_percentage_above_expectation",
                    "aggressiveness",
                ] if x in ngs
            ]
            st.dataframe(ngs[cols].sort_values(["season", "week"], ascending=False), hide_index=True, use_container_width=True)
            for metric in ["avg_intended_air_yards", "completion_percentage_above_expectation"]:
                if metric in ngs.columns and len(ngs) > 1:
                    timeline = ngs.sort_values(["season", "week"]).copy()
                    timeline["Game"] = timeline.season.astype(str) + " W" + timeline.week.astype(str)
                    chart = px.line(timeline, x="Game", y=metric, markers=True, title=metric.replace("_", " ").title())
                    chart.update_layout(
                        height=300,
                        margin=dict(l=10, r=10, t=40, b=10),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(255,255,255,0.03)",
                        font_color="#F6F8FB",
                    )
                    st.plotly_chart(chart, use_container_width=True)
    st.caption("These are player/week aggregates; they do not imply exact play-level coverage identification.")

with pages[6]:
    st.subheader("Every supporting play")
    query = st.text_input("Search play descriptions", placeholder="screen, blitz, third down, right...")
    display = context.copy()
    if query:
        d = display["desc"] if "desc" in display else pd.Series("", index=display.index)
        display = display.loc[d.fillna("").astype(str).str.contains(query, case=False, regex=False)]
    evidence(display, "evidence", caption="Filtered play-level database")

with pages[7]:
    st.subheader("Evidence, field coverage and public data provenance")
    st.dataframe(data_coverage(context), hide_index=True, use_container_width=True)
    a, b = st.columns(2)
    with a:
        st.markdown("**Covered in this release**")
        st.markdown("- Real Broncos play-by-play & EPA\n- Historical personnel and formations when released\n- FTN weekly charting fields where available\n- Weekly Bo Nix NGS summary where available\n- Deterministic questions, evidence downloads and reports")
    with b:
        st.markdown("**Not inferred or promised**")
        st.markdown("- Precise live-season personnel or coverage absent a verified feed\n- Reliable gap/zone/man blocking identification from descriptions\n- Automatically sourced expert film reviews\n- Causal play-call ratings\n- Accounts, fan-submitted notes or shared editable data")
    st.markdown("**Public-data credits:** [nflverse and nflreadpy](https://github.com/nflverse/nflreadpy) (CC BY 4.0 for most sources), [FTN Data via nflverse](https://nflreadr.nflverse.com/reference/load_participation.html) (CC BY-SA 4.0 for FTN contributions), and [NFL Next Gen Stats data dictionary](https://nflreadr.nflverse.com/articles/dictionary_nextgen_stats.html). Preserve applicable attribution/share-alike licensing if you redistribute derived datasets.")
    st.markdown("**Privacy:** The public beta is read-only. No scout notes, names, accounts or personal files are accepted or stored. Data is updated by an external scheduled job, not by visitors.")
    st.caption("Observational comparisons do not control for opponent strength or game script; sample-size labels are descriptive only.")
