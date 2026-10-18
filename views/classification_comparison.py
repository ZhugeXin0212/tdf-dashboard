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
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from db import run_query
from style import insight_card, page_header, seconds_to_hms, shade_gradient, style_fig

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

st.divider()

# ----------------------------------------------------------------------
# Mountain GC proxy: re-rank riders using only their adjusted time on
# Mountain stages, and show where that diverges from the overall GC.
# ----------------------------------------------------------------------
st.subheader("⛰️ Mountain GC Proxy vs Overall GC")
st.caption(
    "A proxy General Classification computed from adjusted time on "
    "Mountain stages only (6 of the 21 stages), compared against the "
    "real overall GC. Large positive differences mean a rider climbs "
    "much better, relative to the field, than their overall result "
    "suggests."
)

mountain_sql = """
    select res.bib, sum(res.time - res.bonus + res.penalty) as mountain_time
    from result res
    join stage s on s.day = res.day
    where s.type = 'mountain'
    group by res.bib
"""
mountain_df = run_query(mountain_sql)
mountain_df["mountain_rank"] = mountain_df["mountain_time"].rank(method="min").astype(int)

mountain_compare = gc_df.merge(mountain_df, on="bib", how="inner")
mountain_compare["rank_diff"] = mountain_compare["gc_rank"] - mountain_compare["mountain_rank"]
mountain_compare = mountain_compare.sort_values("rank_diff", ascending=False)

best_climber = mountain_compare.iloc[0]
insight_card(
    f"<b>{best_climber['rider_name']}</b> ranks <b>{int(best_climber['gc_rank'])}</b> "
    f"overall but <b>{int(best_climber['mountain_rank'])}</b> on Mountain stages alone -- "
    f"the biggest climber-vs-overall divergence in the field."
)

mcol1, mcol2 = st.columns([1.3, 1], gap="medium")

with mcol1:
    top_divergence = pd.concat([mountain_compare.head(8), mountain_compare.tail(8)])
    div_fig = px.bar(
        top_divergence,
        x="rank_diff",
        y="rider_name",
        orientation="h",
        color="rank_diff",
        color_continuous_scale="RdYlGn",
        labels={"rank_diff": "GC rank minus Mountain rank", "rider_name": "Rider"},
        title="Biggest divergences: overall GC rank vs Mountain-only rank",
    )
    div_fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>GC rank: %{customdata[0]}<br>Mountain rank: %{customdata[1]}"
            "<extra></extra>"
        ),
        customdata=top_divergence[["gc_rank", "mountain_rank"]].values,
    )
    div_fig.update_layout(height=500, coloraxis_showscale=False)
    div_fig = style_fig(div_fig)
    st.plotly_chart(div_fig, use_container_width=True)

with mcol2:
    st.markdown("**Top 10 -- Mountain stages only**")
    mountain_top10 = mountain_compare.sort_values("mountain_rank").head(10)[
        ["mountain_rank", "rider_name", "team", "gc_rank"]
    ]
    st.dataframe(
        mountain_top10.rename(
            columns={"mountain_rank": "Mtn. rank", "rider_name": "Rider", "team": "Team", "gc_rank": "Overall GC rank"}
        ),
        hide_index=True,
        use_container_width=True,
        height=400,
    )

st.divider()

# ----------------------------------------------------------------------
# Bonuses, penalties, and a counterfactual GC replay: what would the
# top 10 look like if bonuses (or penalties) didn't exist?
# ----------------------------------------------------------------------
st.subheader("🔁 Bonuses, Penalties & Counterfactual GC")
st.caption(
    "Cumulative time bonuses and penalties earned across the race, and "
    "a replay of the GC top 10 with bonuses or penalties toggled off."
)

bp_sql = """
    select res.bib, sum(res.bonus) as total_bonus, sum(res.penalty) as total_penalty
    from result res
    group by res.bib
"""
bp_df = run_query(bp_sql)
counterfactual = gc_df.merge(bp_df, on="bib", how="left").fillna({"total_bonus": 0, "total_penalty": 0})

toggle = st.radio(
    "Replay GC top 10 with:",
    ["Actual (bonuses + penalties applied)", "No bonuses", "No penalties"],
    horizontal=True,
)
if toggle == "No bonuses":
    # Removing the bonus means that time is added back onto the rider's total.
    counterfactual["cf_time"] = counterfactual["adjusted_time"] + counterfactual["total_bonus"]
elif toggle == "No penalties":
    counterfactual["cf_time"] = counterfactual["adjusted_time"] - counterfactual["total_penalty"]
else:
    counterfactual["cf_time"] = counterfactual["adjusted_time"]

counterfactual["cf_rank"] = counterfactual["cf_time"].rank(method="min").astype(int)
counterfactual["rank_shift"] = counterfactual["gc_rank"] - counterfactual["cf_rank"]
cf_top10 = counterfactual.sort_values("cf_rank").head(10)[
    ["cf_rank", "rider_name", "team", "gc_rank", "rank_shift", "total_bonus", "total_penalty"]
].copy()
cf_top10["cf_time_display"] = counterfactual.sort_values("cf_rank").head(10)["cf_time"].apply(seconds_to_hms)

def _shift_label(v):
    if v == 0:
        return "—"
    return f"▲{v}" if v > 0 else f"▼{abs(v)}"

cf_top10["Movement"] = cf_top10["rank_shift"].apply(_shift_label)

st.dataframe(
    cf_top10[["cf_rank", "rider_name", "team", "cf_time_display", "gc_rank", "Movement"]].rename(
        columns={
            "cf_rank": "New rank",
            "rider_name": "Rider",
            "team": "Team",
            "cf_time_display": "Time under scenario",
            "gc_rank": "Actual GC rank",
        }
    ),
    hide_index=True,
    use_container_width=True,
    column_config={"New rank": st.column_config.NumberColumn("New rank", width="small")},
)
