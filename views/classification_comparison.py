"""
Task 3b -- Classification Comparison: General Classification, Points
Classification, King of the Mountains Classification, Young Rider
Classification.

IMPORTANT DATA LIMITATION
--------------------------
The source data (data/riders.csv, data/individual_results.csv,
data/exits.csv) only records each rider's finish rank, time, bonus and
penalty per stage -- there is no intermediate-sprint or categorized-climb
data. The real UCI Points and King of the Mountains classifications are
scored from those intermediate events, which we do not have.

Points and KOM below are therefore SIMPLIFIED PROXIES built only from
stage finish rank and stage type (flat/hilly/mountain/individual
time-trial), weighted to approximate which stage types favor sprinters
vs climbers. They are clearly labelled as approximations, not the
official UCI scoring, and should be described as such in the project
report.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from db import run_query
from style import page_header, seconds_to_hms, shade_gradient, style_fig

page_header("🏆 Classification Comparison", "General Classification · Points · King of the Mountains · Young Rider")

st.warning(
    "**Simplified proxy classifications.** The raw data has no "
    "intermediate-sprint or climb-category points, so Points and King "
    "of the Mountains below are approximated from stage finish rank, "
    "weighted by stage type (flat/hilly favors sprinters, "
    "mountain/hilly favors climbers). General Classification and Young "
    "Rider use the actual adjusted race time and are not approximations."
)

GC_SQL = """
    select a.rank as gc_rank, a.bib, a.adjusted_time, r.rider_name, r.team, r.dob
    from award_ind a
    join rider r on r.bib = a.bib
"""
gc_df = run_query(GC_SQL)
gc_df["dob"] = pd.to_datetime(gc_df["dob"])

# Young Rider cutoff: UCI defines "young rider" as born on/after Jan 1
# of (race year - 25). The 2023 Tour de France -> cutoff 1998-01-01.
YOUNG_RIDER_CUTOFF = pd.Timestamp("1998-01-01")
young_df = gc_df[gc_df["dob"] >= YOUNG_RIDER_CUTOFF].copy()
young_df["young_rank"] = young_df["adjusted_time"].rank(method="min").astype(int)
young_df = young_df.sort_values("young_rank")

# ----------------------------------------------------------------------
# Points & KOM proxy, computed per stage then summed
# ----------------------------------------------------------------------
PROXY_SQL = """
    select
        res.bib,
        res.rank,
        s.type as stage_type
    from result res
    join stage s on s.day = res.day
"""
proxy_df = run_query(PROXY_SQL)

POINTS_WEIGHT = {"flat": 1.0, "hilly": 0.7, "mountain": 0.3, "individual time-trial": 0.2}
KOM_WEIGHT = {"flat": 0.1, "hilly": 0.6, "mountain": 1.0, "individual time-trial": 0.3}

proxy_df["base_points"] = (21 - proxy_df["rank"]).clip(lower=0)
proxy_df["points_score"] = proxy_df["base_points"] * proxy_df["stage_type"].map(POINTS_WEIGHT)
proxy_df["kom_score"] = proxy_df["base_points"] * proxy_df["stage_type"].map(KOM_WEIGHT)

agg = proxy_df.groupby("bib")[["points_score", "kom_score"]].sum().reset_index()
riders = run_query("select bib, rider_name, team from rider")
agg = agg.merge(riders, on="bib")

points_df = agg.sort_values("points_score", ascending=False).reset_index(drop=True)
points_df["points_rank"] = points_df.index + 1

kom_df = agg.sort_values("kom_score", ascending=False).reset_index(drop=True)
kom_df["kom_rank"] = kom_df.index + 1

# ----------------------------------------------------------------------
# Four classification leaderboards side by side
# ----------------------------------------------------------------------
tab_gc, tab_points, tab_kom, tab_young = st.tabs(
    ["General Classification", "Points (proxy)", "King of the Mountains (proxy)", "Young Rider"]
)

with tab_gc:
    st.caption("Ranked by lowest cumulative adjusted time across all 21 stages.")
    gc_display = gc_df.sort_values("gc_rank").head(20)[["gc_rank", "rider_name", "team", "adjusted_time"]].copy()
    gc_display["Time"] = gc_display["adjusted_time"].apply(seconds_to_hms)
    st.dataframe(
        gc_display[["gc_rank", "rider_name", "team", "adjusted_time", "Time"]].rename(
            columns={"gc_rank": "Rank", "rider_name": "Rider", "team": "Team"}
        ),
        hide_index=True,
        use_container_width=True,
        column_config={
            "Rank": st.column_config.NumberColumn("Rank", width="small"),
            "adjusted_time": st.column_config.ProgressColumn(
                "Relative pace", min_value=float(gc_display["adjusted_time"].min()),
                max_value=float(gc_display["adjusted_time"].max()), format=" ",
            ),
        },
    )

with tab_points:
    st.caption("Simplified proxy -- higher score rewards consistent high finishes on flat/hilly stages.")
    pts_display = points_df.head(20)[["points_rank", "rider_name", "team", "points_score"]].copy()
    st.dataframe(
        pts_display.rename(columns={"points_rank": "Rank", "rider_name": "Rider", "team": "Team"}),
        hide_index=True,
        use_container_width=True,
        column_config={
            "Rank": st.column_config.NumberColumn("Rank", width="small"),
            "points_score": st.column_config.ProgressColumn(
                "Score (proxy)", min_value=0.0, max_value=float(pts_display["points_score"].max()), format="%.1f",
            ),
        },
    )

with tab_kom:
    st.caption("Simplified proxy -- higher score rewards consistent high finishes on mountain/hilly stages.")
    kom_display = kom_df.head(20)[["kom_rank", "rider_name", "team", "kom_score"]].copy()
    st.dataframe(
        kom_display.rename(columns={"kom_rank": "Rank", "rider_name": "Rider", "team": "Team"}),
        hide_index=True,
        use_container_width=True,
        column_config={
            "Rank": st.column_config.NumberColumn("Rank", width="small"),
            "kom_score": st.column_config.ProgressColumn(
                "Score (proxy)", min_value=0.0, max_value=float(kom_display["kom_score"].max()), format="%.1f",
            ),
        },
    )

with tab_young:
    st.caption(f"Riders born on/after {YOUNG_RIDER_CUTOFF.date()} (age 25 or under during the race), ranked by adjusted time.")
    young_display = young_df.head(20)[["young_rank", "rider_name", "team", "adjusted_time"]].copy()
    young_display["Time"] = young_display["adjusted_time"].apply(seconds_to_hms)
    st.dataframe(
        young_display.rename(columns={"young_rank": "Rank", "rider_name": "Rider", "team": "Team"}),
        hide_index=True,
        use_container_width=True,
        column_config={"Rank": st.column_config.NumberColumn("Rank", width="small")},
    )

st.divider()

# ----------------------------------------------------------------------
# Cross-classification comparison for a single rider
# ----------------------------------------------------------------------
st.subheader("Compare a rider's rank across all four classifications")
rider_name = st.selectbox("Select a rider", sorted(riders["rider_name"].tolist()))
bib = riders.loc[riders["rider_name"] == rider_name, "bib"].iloc[0]

gc_rank = gc_df.loc[gc_df["bib"] == bib, "gc_rank"]
points_rank = points_df.loc[points_df["bib"] == bib, "points_rank"]
kom_rank = kom_df.loc[kom_df["bib"] == bib, "kom_rank"]
young_rank = young_df.loc[young_df["bib"] == bib, "young_rank"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("GC rank", int(gc_rank.iloc[0]) if len(gc_rank) else "DNF")
c2.metric("Points rank (proxy)", int(points_rank.iloc[0]) if len(points_rank) else "N/A")
c3.metric("KOM rank (proxy)", int(kom_rank.iloc[0]) if len(kom_rank) else "N/A")
c4.metric("Young Rider rank", int(young_rank.iloc[0]) if len(young_rank) else "Not eligible")

compare_df = pd.DataFrame(
    {
        "classification": ["GC", "Points (proxy)", "KOM (proxy)", "Young Rider"],
        "rank": [
            int(gc_rank.iloc[0]) if len(gc_rank) else None,
            int(points_rank.iloc[0]) if len(points_rank) else None,
            int(kom_rank.iloc[0]) if len(kom_rank) else None,
            int(young_rank.iloc[0]) if len(young_rank) else None,
        ],
    }
)
compare_df = compare_df[compare_df["rank"].notna()].reset_index(drop=True)

# One solid base hue per classification (not a mixed/arbitrary palette),
# each rendered as a light-to-dark gradient along the bar's length to
# give a sense of depth, plus a soft offset shadow trace for a subtle
# pseudo-3D "raised" look. Bars point right (horizontal) and are drawn
# thin per the requested look.
BASE_HUES = {
    "GC": "#E6A817",
    "Points (proxy)": "#2E7D32",
    "KOM (proxy)": "#D32F2F",
    "Young Rider": "#1565C0",
}
BAR_WIDTH = 0.4
N_SEGMENTS = 30
max_rank = float(compare_df["rank"].max()) if len(compare_df) else 1.0
shadow_offset = max_rank * 0.015

# Numeric y positions (one per category, top-to-bottom) so a shadow
# trace can be nudged diagonally behind the real bar.
compare_df["y_pos"] = range(len(compare_df) - 1, -1, -1)

compare_fig = go.Figure()

for _, row in compare_df.iterrows():
    cat, value, y_pos = row["classification"], float(row["rank"]), row["y_pos"]
    base_hue = BASE_HUES.get(cat, "#555555")

    # Drop-shadow bar: same length, nudged down-right, translucent dark.
    compare_fig.add_trace(
        go.Bar(
            y=[y_pos - 0.18], x=[value], base=[shadow_offset], orientation="h",
            width=BAR_WIDTH, marker=dict(color="rgba(0,0,0,0.14)", line=dict(width=0)),
            showlegend=False, hoverinfo="skip",
        )
    )

    # Light-to-dark gradient fill: many thin stacked segments along x.
    seg_len = value / N_SEGMENTS
    gradient_colors = shade_gradient(base_hue, N_SEGMENTS)
    for i, seg_color in enumerate(gradient_colors):
        compare_fig.add_trace(
            go.Bar(
                y=[y_pos], x=[seg_len], base=[i * seg_len], orientation="h",
                width=BAR_WIDTH,
                marker=dict(color=seg_color, line=dict(width=0)),
                showlegend=False, hoverinfo="skip",
            )
        )

    # Invisible full-length overlay on top purely to carry the hover tooltip.
    compare_fig.add_trace(
        go.Bar(
            y=[y_pos], x=[value], base=[0], orientation="h",
            width=BAR_WIDTH, marker=dict(color="rgba(0,0,0,0)"),
            showlegend=False,
            hovertemplate=f"<b>{cat}</b><br>Rank: {int(value)}<extra></extra>",
        )
    )

compare_fig.update_layout(
    title=f"{rider_name}'s rank across classifications (lower is better)",
    barmode="overlay",
    bargap=0.4,
    yaxis=dict(
        tickmode="array",
        tickvals=compare_df["y_pos"].tolist(),
        ticktext=compare_df["classification"].tolist(),
    ),
    xaxis=dict(title="Rank"),
    height=120 * max(len(compare_df), 1) + 120,
)
compare_fig = style_fig(compare_fig)
st.plotly_chart(compare_fig, use_container_width=True)
