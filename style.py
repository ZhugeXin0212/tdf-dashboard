"""
Shared visual styling and reusable UI components for every page of the
dashboard.

Design decisions, informed by a review of Tableau / Power BI / Grafana
conventions:
  - Limit each screen to a handful of focused views (Tableau's "2-3
    views per dashboard" guidance) rather than a wall of charts.
  - KPI cards show a headline number + a delta/trend, not a bare
    number (Power BI "New Card" / SaaS "hero metric" pattern).
  - Every chart gets a custom multi-line hover tooltip (hovertemplate)
    instead of Plotly's default single-field hover.
  - Colorway is colorblind-safe (Okabe-Ito inspired) with at most ~8
    hues, and color is never the only encoding of meaning (labels /
    patterns are added where it matters).

Call `apply_global_style()` right after `st.set_page_config(...)` on
every page so the look is consistent across the whole app.
"""

import streamlit as st

CUSTOM_CSS = """
<style>
/* ---------- Overall page padding ---------- */
.block-container {
    padding-top: 1.6rem;
    padding-bottom: 3rem;
    max-width: 1400px;
}

/* ---------- Header banner ---------- */
.tdf-header {
    background: linear-gradient(100deg, #FFC72C 0%, #FFD966 55%, #FFE799 100%);
    border-radius: 16px;
    padding: 1.5rem 2rem;
    margin-bottom: 1.4rem;
    box-shadow: 0 4px 14px rgba(0,0,0,0.10);
    position: relative;
    overflow: hidden;
}
.tdf-header::after {
    content: "";
    position: absolute;
    right: -40px;
    top: -40px;
    width: 160px;
    height: 160px;
    background: rgba(255,255,255,0.25);
    border-radius: 50%;
}
.tdf-header h1 {
    color: #1A1A1A;
    margin: 0 0 0.3rem 0;
    font-size: 2.0rem;
    font-weight: 800;
    letter-spacing: -0.02em;
}
.tdf-header p {
    color: #3b3b3b;
    margin: 0;
    font-size: 0.98rem;
    max-width: 75%;
}

/* ---------- Metric cards ---------- */
div[data-testid="stMetric"] {
    background-color: #FFFFFF;
    border: 1px solid #ECECEC;
    border-radius: 12px;
    padding: 0.9rem 1.1rem 0.7rem 1.1rem;
    box-shadow: 0 1px 5px rgba(0,0,0,0.05);
    transition: box-shadow 0.15s ease;
}
div[data-testid="stMetric"]:hover {
    box-shadow: 0 4px 14px rgba(0,0,0,0.10);
}
div[data-testid="stMetricLabel"] {
    font-weight: 600;
    color: #555555;
    font-size: 0.85rem;
}
div[data-testid="stMetricValue"] {
    color: #1A1A1A;
    font-size: 1.6rem;
}
div[data-testid="stMetricDelta"] svg {
    display: inline;
}

/* ---------- Insight / callout card ---------- */
.tdf-insight {
    background-color: #FFF8E6;
    border-left: 4px solid #FFC72C;
    border-radius: 8px;
    padding: 0.85rem 1.1rem;
    margin: 0.6rem 0 1.2rem 0;
    font-size: 0.95rem;
    color: #333333;
}
.tdf-insight b { color: #1A1A1A; }

/* ---------- Section subheaders ---------- */
h2, h3 {
    color: #1A1A1A;
    font-weight: 700;
}

/* ---------- Card container (st.container(border=True)) ---------- */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 12px !important;
}

/* ---------- Dataframe / table container ---------- */
div[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #ECECEC;
}

/* ---------- Tabs ---------- */
button[data-baseweb="tab"] {
    font-weight: 600;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #B8860B;
}
div[data-baseweb="tab-highlight"] {
    background-color: #FFC72C !important;
}

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {
    background-color: #FAFAFA;
    border-right: 1px solid #ECECEC;
}

/* ---------- Divider spacing ---------- */
hr {
    margin: 1.2rem 0;
}

/* ---------- Badges (used for small inline labels) ---------- */
.tdf-badge {
    display: inline-block;
    padding: 0.15rem 0.6rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 700;
    margin-right: 0.4rem;
}
.tdf-badge-yellow { background: #FFF1C2; color: #8a6700; }
.tdf-badge-green  { background: #DFF3E0; color: #1E5E22; }
.tdf-badge-red    { background: #FBE0E0; color: #9A1F1F; }
.tdf-badge-blue   { background: #DCEBFB; color: #0E4C92; }

/* ---------- Business-question banner ---------- */
.tdf-question {
    background: #F6F7FA;
    border: 1px solid #E3E6EE;
    border-radius: 10px;
    padding: 0.7rem 1.1rem;
    margin: -0.4rem 0 1.1rem 0;
    font-size: 0.97rem;
    color: #333;
}
.tdf-question .q { font-weight: 800; color: #1A1A1A; }
.tdf-question .a { color: #555; font-size: 0.9rem; margin-top: 0.2rem; }

/* ---------- Section kicker (numbered storyline step) ---------- */
.tdf-section {
    display: flex; align-items: baseline; gap: 0.6rem;
    margin: 1.4rem 0 0.2rem 0;
}
.tdf-section .num {
    background: #1A1A1A; color: #FFC72C; font-weight: 800;
    border-radius: 6px; padding: 0.05rem 0.5rem; font-size: 0.85rem;
}
.tdf-section .ttl { font-size: 1.3rem; font-weight: 800; color: #1A1A1A; }
.tdf-section .tag { font-size: 0.78rem; color: #8a6700; background: #FFF1C2;
    border-radius: 999px; padding: 0.05rem 0.55rem; font-weight: 700; }

/* ---------- Finding card (headline insight with a big number) ---------- */
.tdf-finding {
    background: #FFFFFF;
    border: 1px solid #ECECEC;
    border-top: 4px solid var(--accent, #FFC72C);
    border-radius: 12px;
    padding: 0.85rem 1rem 0.75rem 1rem;
    box-shadow: 0 1px 5px rgba(0,0,0,0.05);
    height: 100%;
}
.tdf-finding .k { font-size: 0.75rem; font-weight: 800; letter-spacing: 0.04em;
    text-transform: uppercase; color: var(--accent, #B8860B); }
.tdf-finding .v { font-size: 1.55rem; font-weight: 800; color: #1A1A1A; margin: 0.15rem 0; line-height: 1.15; }
.tdf-finding .t { font-size: 0.88rem; color: #444; line-height: 1.4; }
.tdf-finding { min-height: 150px; }

/* ---------- KPI tiles (wrap long text instead of truncating) ---------- */
.tdf-kpis { display: grid; gap: 0.7rem; margin: 0.2rem 0 0.6rem 0; }
.tdf-kpi {
    background: #FFFFFF; border: 1px solid #ECECEC; border-radius: 12px;
    padding: 0.7rem 0.9rem; box-shadow: 0 1px 5px rgba(0,0,0,0.05);
}
.tdf-kpi .l { font-size: 0.8rem; font-weight: 600; color: #666; }
.tdf-kpi .v { font-size: 1.25rem; font-weight: 800; color: #1A1A1A; line-height: 1.2; margin: 0.15rem 0; }
.tdf-kpi .s { font-size: 0.8rem; color: #8a6700; }

/* ---------- "So what" / recommendation box ---------- */
.tdf-sowhat {
    background: linear-gradient(100deg, #EEF6EE 0%, #F7FBF7 100%);
    border-left: 5px solid #2E7D32;
    border-radius: 10px;
    padding: 0.85rem 1.2rem;
    margin: 0.8rem 0 1.2rem 0;
    font-size: 0.94rem;
    color: #1f3b20;
}
.tdf-sowhat .h { font-weight: 800; color: #1E5E22; margin-bottom: 0.3rem; }
.tdf-sowhat ul { margin: 0.2rem 0 0 1.1rem; padding: 0; }
.tdf-sowhat li { margin: 0.15rem 0; }
.tdf-sowhat b { color: #123a14; }
</style>
"""


def apply_global_style() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "") -> None:
    """Render a consistent gradient banner header used at the top of
    every page, instead of plain st.title()."""
    subtitle_html = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div class="tdf-header">
            <h1>{title}</h1>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def insight_card(markdown_text: str) -> None:
    """A highlighted callout box for a single key takeaway, styled
    distinctly from st.info/st.caption so it reads as 'the one thing
    to notice here' (the SaaS 'hero insight' pattern)."""
    st.markdown(f'<div class="tdf-insight">💡 {markdown_text}</div>', unsafe_allow_html=True)


def badge(text: str, color: str = "yellow") -> str:
    """Return an inline HTML badge snippet (yellow/green/red/blue)."""
    return f'<span class="tdf-badge tdf-badge-{color}">{text}</span>'


# ----------------------------------------------------------------------
# Colorblind-safe palette (Okabe-Ito inspired) + jersey semantics.
# Capped at 8 hues per onscreen best-practice guidance; color is never
# the sole encoding -- labels/legends/hover text repeat the same info.
# ----------------------------------------------------------------------
TDF_COLORWAY = [
    "#E6A817",  # yellow jersey (muted gold, readable on white)
    "#1565C0",  # strong blue
    "#2E7D32",  # green jersey (points)
    "#D32F2F",  # polka-dot jersey (KOM) red
    "#6A1B9A",  # purple
    "#00897B",  # teal
    "#EF6C00",  # orange
    "#5D4037",  # brown
]

SEQUENTIAL_SCALE = "YlOrRd"       # for "more is more intense" bar/map charts
DIVERGING_SCALE = "RdYlGn"        # for gap/above-below comparisons

HOVER_LABEL_STYLE = dict(
    bgcolor="#1A1A1A",
    font=dict(color="#FFFFFF", size=13),
    bordercolor="#1A1A1A",
)


def style_fig(fig, hovermode: str = "closest"):
    """Apply the shared colorway, clean layout, and a dark unified
    hover-label style to a Plotly figure. Call this last, after you've
    already set any custom hovertemplate on the traces."""
    fig.update_layout(
        colorway=TDF_COLORWAY,
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        font=dict(color="#1A1A1A", family="sans-serif"),
        margin=dict(l=20, r=20, t=60, b=20),
        legend=dict(bgcolor="rgba(255,255,255,0.7)", bordercolor="#ECECEC", borderwidth=1),
        hovermode=hovermode,
        hoverlabel=HOVER_LABEL_STYLE,
        title_font=dict(size=16, color="#1A1A1A"),
    )
    fig.update_xaxes(gridcolor="#F0F0F0", zerolinecolor="#E0E0E0")
    fig.update_yaxes(gridcolor="#F0F0F0", zerolinecolor="#E0E0E0")
    return fig


def shade_gradient(base_hex: str, n: int, light_mix: float = 0.68, dark_mix: float = 0.35) -> list[str]:
    """Return n hex colors interpolating from a light tint to a dark
    tint of a single base hue -- used to fake a smooth light-to-dark
    gradient fill on a single-color bar (one hue per bar, not a
    multi-hue scale), by drawing many thin stacked segments.
    """
    base = tuple(int(base_hex.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    white, black = (255, 255, 255), (0, 0, 0)
    light = tuple(base[i] + (white[i] - base[i]) * light_mix for i in range(3))
    dark = tuple(base[i] + (black[i] - base[i]) * dark_mix for i in range(3))
    out = []
    for step in range(n):
        t = step / (n - 1) if n > 1 else 0
        rgb = tuple(light[i] + (dark[i] - light[i]) * t for i in range(3))
        out.append("#%02x%02x%02x" % tuple(max(0, min(255, int(round(c)))) for c in rgb))
    return out


def seconds_to_hms(seconds) -> str:
    """Format a race-time value in seconds as 'Hh Mm Ss' for display
    in tables, metrics, and hover tooltips."""
    try:
        s = int(seconds)
    except (TypeError, ValueError):
        return "N/A"
    sign = "-" if s < 0 else ""
    s = abs(s)
    return f"{sign}{s // 3600}h {(s % 3600) // 60}m {s % 60}s"


# ----------------------------------------------------------------------
# Storytelling components (business-dashboard pattern):
#   question -> headline finding -> evidence chart -> "so what".
# ----------------------------------------------------------------------
STAGE_TYPE_ORDER = ["flat", "hilly", "mountain", "individual time-trial"]
STAGE_TYPE_LABEL = {
    "flat": "Flat",
    "hilly": "Hilly",
    "mountain": "Mountain",
    "individual time-trial": "ITT",
}
STAGE_TYPE_COLORS = {
    "Flat": "#2E7D32",
    "Hilly": "#EF6C00",
    "Mountain": "#D32F2F",
    "ITT": "#1565C0",
}


def business_question(question: str, answer_hint: str = "") -> None:
    """Grey banner under the page header stating the business question
    the page answers (and, optionally, who should care)."""
    hint = f'<div class="a">{answer_hint}</div>' if answer_hint else ""
    st.markdown(
        f'<div class="tdf-question"><span class="q">❓ Business question:</span> {question}{hint}</div>',
        unsafe_allow_html=True,
    )


def section(num: str, title: str, tag: str = "") -> None:
    """Numbered section heading so each page reads as a storyline."""
    tag_html = f'<span class="tag">{tag}</span>' if tag else ""
    st.markdown(
        f'<div class="tdf-section"><span class="num">{num}</span>'
        f'<span class="ttl">{title}</span>{tag_html}</div>',
        unsafe_allow_html=True,
    )


def finding_card(kicker: str, value: str, text: str, accent: str = "#E6A817") -> None:
    """Headline-insight card: small kicker, big number, one-line meaning."""
    st.markdown(
        f'<div class="tdf-finding" style="--accent:{accent}">'
        f'<div class="k">{kicker}</div><div class="v">{value}</div>'
        f'<div class="t">{text}</div></div>',
        unsafe_allow_html=True,
    )


def so_what(points: list[str], title: str = "So what? — implications") -> None:
    """Green recommendation box that turns the evidence into actions."""
    items = "".join(f"<li>{p}</li>" for p in points)
    st.markdown(
        f'<div class="tdf-sowhat"><div class="h">✅ {title}</div><ul>{items}</ul></div>',
        unsafe_allow_html=True,
    )


def fmt_gap(seconds) -> str:
    """Compact race-gap format: 4m 24s / 58s / — for zero."""
    try:
        s = int(round(float(seconds)))
    except (TypeError, ValueError):
        return "N/A"
    if s == 0:
        return "—"
    sign = "-" if s < 0 else "+"
    s = abs(s)
    if s >= 3600:
        return f"{sign}{s // 3600}h {(s % 3600) // 60:02d}m {s % 60:02d}s"
    if s >= 60:
        return f"{sign}{s // 60}m {s % 60:02d}s"
    return f"{sign}{s}s"


_ACRONYMS = {"UAE", "XRG", "EF", "FDJ", "XDS", "AG2R", "B&B"}


def short_team(name: str) -> str:
    """Readable short team name for cards: 'TEAM VISMA | LEASE A BIKE' ->
    'Team Visma', 'UAE TEAM EMIRATES XRG' -> 'UAE Team Emirates XRG'."""
    if not isinstance(name, str):
        return ""
    head = name.split("|")[0].strip()

    def fix(word: str) -> str:
        return "-".join(p if p in _ACRONYMS else p.capitalize() for p in word.split("-"))

    return " ".join(fix(w) for w in head.split())


def kpi_row(items: list[tuple[str, str, str]]) -> None:
    """Row of KPI tiles (label, value, sub-text). Unlike st.metric the
    value wraps instead of being truncated, which matters for names."""
    tiles = "".join(
        f'<div class="tdf-kpi"><div class="l">{l}</div><div class="v">{v}</div><div class="s">{s}</div></div>'
        for l, v, s in items
    )
    st.markdown(
        f'<div class="tdf-kpis" style="grid-template-columns:repeat({len(items)},1fr)">{tiles}</div>',
        unsafe_allow_html=True,
    )
