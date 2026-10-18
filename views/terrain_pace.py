"""
Task 3e -- Terrain & Pace Analysis: mountain-specific signals for
riders, and a stage-type speed/pace profile across Flat, Hilly,
Mountain, and ITT terrain.

This page adds two analyses that aren't covered elsewhere:
  - Mountain contours (E5): podium frequency on Mountain stages, and
    mean time gap to the stage winner on that terrain.
  - Speed as a simple ratio (E6): a distance/time pace proxy per stage
    type, for riders and teams, highlighting who gains when terrain
    shifts from Flat/Hilly toward Mountain.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from db import run_query
from style import insight_card, page_header, style_fig

page_header(
    "⛰️ Terrain & Pace Analysis",
    "Mountain-specific performance signals, and how riders/teams pace themselves across stage types.",
)

# ----------------------------------------------------------------------
# Mountain contours: podium frequency + mean gap to stage winner
# ----------------------------------------------------------------------
st.subheader("🏔️ Mountain Contours")
st.caption(
    "For each rider, how often they podium (top 3) on Mountain stages, "
    "and on average how far behind the stage winner they finish on "
    "that terrain."
)

mountain_results_sql = """
    select res.bib, r.rider_name, r.team, res.rank,
           (res.time - res.bonus + res.penalty) as adjusted_time, s.day
    from result res
    join stage s on s.day = res.day
    join rider r on r.bib = res.bib
    where s.type = 'mountain'
"""
mountain_results = run_query(mountain_results_sql)

winner_time_by_day = (
    mountain_results.loc[mountain_results["rank"] == 1]
    .set_index("day")["adjusted_time"]
)
mountain_results["gap_to_winner"] = mountain_results.apply(
    lambda row: row["adjusted_time"] - winner_time_by_day.get(row["day"], row["adjusted_time"]), axis=1
)

mountain_summary = (
    mountain_results.groupby(["bib", "rider_name", "team"])
    .agg(
        podiums=("rank", lambda s: int((s <= 3).sum())),
        stages_ridden=("rank", "count"),
        avg_gap=("gap_to_winner", "mean"),
    )
    .reset_index()
)
mountain_summary = mountain_summary.sort_values(["podiums", "avg_gap"], ascending=[False, True])

best_climber = mountain_summary.iloc[0]
insight_card(
    f"<b>{best_climber['rider_name']}</b> ({best_climber['team']}) podiumed on "
    f"<b>{int(best_climber['podiums'])}</b> of the 6 Mountain stages -- the most "
    f"of any rider -- with an average gap to the stage winner of just "
    f"<b>{best_climber['avg_gap']:.0f}s</b>."
)

mcol1, mcol2 = st.columns([1.3, 1], gap="medium")

with mcol1:
    top_climbers = mountain_summary.head(15)
    podium_fig = px.bar(
        top_climbers,
        x="podiums",
        y="rider_name",
        orientation="h",
        color="avg_gap",
        color_continuous_scale="RdYlGn_r",
        labels={"podiums": "Mountain podiums", "rider_name": "Rider", "avg_gap": "Avg. gap to winner (s)"},
        title="Most frequent Mountain-stage podium finishers",
    )
    podium_fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>Mountain podiums: %{x}<br>Avg. gap to winner: %{marker.color:.0f}s"
            "<extra></extra>"
        )
    )
    podium_fig.update_layout(height=500, yaxis=dict(autorange="reversed"))
    podium_fig = style_fig(podium_fig)
    st.plotly_chart(podium_fig, use_container_width=True)

with mcol2:
    st.markdown("**Smallest avg. gap to Mountain stage winner**")
    st.caption("Among riders who finished at least 3 of the 6 Mountain stages.")
    consistent_climbers = mountain_summary[mountain_summary["stages_ridden"] >= 3].sort_values("avg_gap").head(10)
    st.dataframe(
        consistent_climbers[["rider_name", "team", "podiums", "avg_gap"]].rename(
            columns={
                "rider_name": "Rider", "team": "Team", "podiums": "Podiums",
                "avg_gap": "Avg. gap (s)",
            }
        ).round({"Avg. gap (s)": 0}),
        hide_index=True,
        use_container_width=True,
        height=400,
    )

st.divider()

# ----------------------------------------------------------------------
# Speed as a simple ratio: distance/time pace profile per stage type
# ----------------------------------------------------------------------
st.subheader("🚀 Pace Profile by Terrain")
st.caption(
    "A simple speed proxy (stage distance ÷ adjusted time) per stage "
    "type, for a chosen rider or team. Highlights who speeds up or "
    "slows down as terrain shifts from Flat/Hilly toward Mountain."
)

pace_sql = """
    select
        res.bib, r.rider_name, r.team, s.type as stage_type,
        s.length, (res.time - res.bonus + res.penalty) as adjusted_time
    from result res
    join stage s on s.day = res.day
    join rider r on r.bib = res.bib
"""
pace_df = run_query(pace_sql)
pace_df["pace_kmh"] = pace_df["length"] / (pace_df["adjusted_time"] / 3600.0)

view_mode = st.radio("Compare by", ["Rider", "Team"], horizontal=True)
STAGE_TYPE_ORDER = ["flat", "hilly", "mountain", "individual time-trial"]

if view_mode == "Rider":
    riders_list = sorted(pace_df["rider_name"].unique().tolist())
    picked_riders = st.multiselect(
        "Select riders", riders_list, default=riders_list[:3] if len(riders_list) >= 3 else riders_list
    )
    pace_plot_df = (
        pace_df[pace_df["rider_name"].isin(picked_riders)]
        .groupby(["rider_name", "stage_type"])["pace_kmh"].mean()
        .reset_index()
    )
    color_col, label_col = "rider_name", "Rider"
else:
    teams_list = sorted(pace_df["team"].unique().tolist())
    picked_teams_pace = st.multiselect(
        "Select teams", teams_list, default=teams_list[:3] if len(teams_list) >= 3 else teams_list
    )
    pace_plot_df = (
        pace_df[pace_df["team"].isin(picked_teams_pace)]
        .groupby(["team", "stage_type"])["pace_kmh"].mean()
        .reset_index()
    )
    color_col, label_col = "team", "Team"

if len(pace_plot_df):
    # Stage type is a category, not a continuous axis -- flat/hilly/
    # mountain/ITT have no meaningful "distance" between them (ITT in
    # particular isn't a point further along a flat->mountain
    # gradient, it's a different race format). A line chart implies a
    # continuous progression and visually "doubles back" whenever a
    # rider's ITT pace sits between their flat and mountain pace.
    # Grouped bars compare each stage type independently with no such
    # implied ordering, so there's no fold-back artifact.
    pace_fig = px.bar(
        pace_plot_df,
        x="stage_type",
        y="pace_kmh",
        color=color_col,
        barmode="group",
        category_orders={"stage_type": STAGE_TYPE_ORDER},
        labels={"stage_type": "Stage type", "pace_kmh": "Avg. pace (km/h)", color_col: label_col},
        title="Average pace by stage type",
    )
    pace_fig.update_traces(
        hovertemplate="<b>%{fullData.name}</b><br>%{x}: %{y:.1f} km/h<extra></extra>"
    )
    pace_fig.update_layout(height=480, bargap=0.25, bargroupgap=0.08)
    pace_fig = style_fig(pace_fig)
    st.plotly_chart(pace_fig, use_container_width=True)
else:
    st.info("Select at least one rider or team above to see their pace profile.")
