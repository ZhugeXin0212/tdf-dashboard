"""
Task 3c -- Aggregate Performance Analysis: cumulative race times by
rider, team and classification. This page is what the gc_standing
table (built specifically for this dashboard) supports: a day-by-day
cumulative time series, not just the final snapshot in award_ind /
award_team.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from db import run_query
from style import insight_card, page_header, seconds_to_hms, style_fig

page_header(
    "📈 Aggregate Performance Analysis",
    "Cumulative adjusted time and General Classification rank, recalculated after every stage.",
)

riders = run_query("select bib, rider_name, team from rider order by rider_name")
teams = run_query("select team from team order by team")

tab_rider, tab_team = st.tabs(["By rider", "By team"])

# ----------------------------------------------------------------------
# Rider-level cumulative trend
# ----------------------------------------------------------------------
with tab_rider:
    default_riders = riders["rider_name"].head(3).tolist()
    picked = st.multiselect(
        "Select riders to compare (cumulative time trend)",
        riders["rider_name"].tolist(),
        default=default_riders,
    )
    picked_bibs = riders.loc[riders["rider_name"].isin(picked), "bib"].tolist()

    stage_types = run_query("select day, type from stage order by day")
    mountain_days = set(stage_types.loc[stage_types["type"] == "mountain", "day"])

    if picked_bibs:
        trend_sql = """
            select g.day, g.bib, r.rider_name, g.cumulative_time, g.gc_rank
            from gc_standing g
            join rider r on r.bib = g.bib
            where g.bib = any(%(bibs)s)
            order by g.day
        """
        trend_df = run_query(trend_sql, {"bibs": picked_bibs})

        metric = st.radio(
            "Metric", ["Cumulative adjusted time (s)", "GC rank on that day"], horizontal=True
        )
        y_col = "cumulative_time" if metric.startswith("Cumulative") else "gc_rank"

        fig = px.line(
            trend_df,
            x="day",
            y=y_col,
            color="rider_name",
            markers=True,
            labels={"day": "Stage date", y_col: metric, "rider_name": "Rider"},
            title=f"{metric} across the 2023 Tour de France",
        )
        if y_col == "gc_rank":
            fig.update_yaxes(autorange="reversed")
            fig.update_traces(
                hovertemplate="<b>%{fullData.name}</b><br>Date: %{x}<br>GC rank: %{y}<extra></extra>"
            )
        else:
            fig.update_traces(
                hovertemplate="<b>%{fullData.name}</b><br>Date: %{x}<br>Cumulative time: %{y:.0f}s<extra></extra>"
            )

        # Shade Mountain stage days so the terrain context is visible
        # directly on the timeline, not just implied by the data.
        for mday in mountain_days:
            fig.add_vrect(
                x0=mday, x1=mday,
                fillcolor="#D32F2F", opacity=0.08, layer="below", line_width=0,
            )

        # Auto-detect the single biggest GC-rank swing for each selected
        # rider (the "pivotal stage") and annotate it directly on the
        # chart -- this is the "contextual descent" insight from E1.
        pivotal_notes = []
        for bib, name in zip(picked_bibs, trend_df.loc[trend_df["bib"].isin(picked_bibs), "rider_name"].unique()):
            rider_trend = trend_df[trend_df["bib"] == bib].sort_values("day").reset_index(drop=True)
            if len(rider_trend) < 2:
                continue
            rider_trend["rank_swing"] = rider_trend["gc_rank"].diff().abs()
            pivot_idx = rider_trend["rank_swing"].idxmax()
            if pd.isna(rider_trend.loc[pivot_idx, "rank_swing"]) or rider_trend.loc[pivot_idx, "rank_swing"] == 0:
                continue
            pivot_row = rider_trend.loc[pivot_idx]
            pivotal_notes.append((name, pivot_row["day"], int(rider_trend.loc[pivot_idx, "rank_swing"])))
            fig.add_annotation(
                x=pivot_row["day"],
                y=pivot_row[y_col],
                text="★",
                showarrow=True,
                arrowhead=2,
                ax=0, ay=-30,
                font=dict(size=16, color="#B8860B"),
            )

        fig.update_layout(height=550, hovermode="x unified")
        fig = style_fig(fig, hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("🔴 Shaded columns = Mountain stages. ★ = each rider's single biggest GC-rank swing (their pivotal stage).")

        if pivotal_notes:
            lines = "<br>".join(
                f"<b>{name}</b>: biggest GC move on <b>{day}</b> ({swing} place{'s' if swing != 1 else ''})"
                for name, day, swing in pivotal_notes
            )
            insight_card(lines)
    else:
        st.info("Select at least one rider above to see their cumulative trend.")

# ----------------------------------------------------------------------
# Team-level cumulative trend (avg of the team's riders still in the race)
# ----------------------------------------------------------------------
with tab_team:
    picked_teams = st.multiselect(
        "Select teams to compare (average cumulative time of active riders)",
        teams["team"].tolist(),
        default=teams["team"].head(3).tolist(),
    )

    if picked_teams:
        team_trend_sql = """
            select g.day, r.team, avg(g.cumulative_time) as avg_cumulative_time
            from gc_standing g
            join rider r on r.bib = g.bib
            where r.team = any(%(teams)s)
            group by g.day, r.team
            order by g.day
        """
        team_trend_df = run_query(team_trend_sql, {"teams": picked_teams})

        fig2 = px.line(
            team_trend_df,
            x="day",
            y="avg_cumulative_time",
            color="team",
            markers=True,
            labels={"day": "Stage date", "avg_cumulative_time": "Avg. cumulative time (s)", "team": "Team"},
            title="Average cumulative adjusted time of riders still racing, by team",
        )
        fig2.update_traces(
            hovertemplate="<b>%{fullData.name}</b><br>Date: %{x}<br>Avg. cumulative time: %{y:.0f}s<extra></extra>"
        )
        fig2.update_layout(height=550, hovermode="x unified")
        fig2 = style_fig(fig2, hovermode="x unified")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Select at least one team above to see its cumulative trend.")

st.divider()

# ----------------------------------------------------------------------
# Gap-to-leader over time for the final top 5
# ----------------------------------------------------------------------
st.subheader("⏱️ Gap to the eventual winner, stage by stage")
st.caption(
    "For the final top 5 finishers, shows how far behind the eventual "
    "winner's cumulative time they were after each stage."
)

top5_sql = """
    select a.bib, r.rider_name
    from award_ind a
    join rider r on r.bib = a.bib
    order by a.rank
    limit 5
"""
top5 = run_query(top5_sql)
top5_bibs = top5["bib"].tolist()

gap_sql = """
    select day, bib, cumulative_time
    from gc_standing
    where bib = any(%(bibs)s)
    order by day
"""
gap_df = run_query(gap_sql, {"bibs": top5_bibs})
winner_bib = top5_bibs[0]
winner_time = gap_df[gap_df["bib"] == winner_bib].set_index("day")["cumulative_time"]
gap_df["gap_to_winner"] = gap_df.apply(
    lambda row: row["cumulative_time"] - winner_time.get(row["day"], row["cumulative_time"]), axis=1
)
gap_df = gap_df.merge(top5, on="bib")

final_gap = gap_df.sort_values("day").groupby("rider_name").tail(1)
runner_up_gap = final_gap.loc[final_gap["gap_to_winner"] > 0, "gap_to_winner"].min()
if pd.notna(runner_up_gap):
    insight_card(
        f"The runner-up finished <b>{seconds_to_hms(runner_up_gap)}</b> behind the winner "
        f"after 21 stages — hover any line below to see the gap at a specific stage."
    )

fig3 = px.line(
    gap_df,
    x="day",
    y="gap_to_winner",
    color="rider_name",
    markers=True,
    labels={"day": "Stage date", "gap_to_winner": "Gap to winner (s)", "rider_name": "Rider"},
    title="Time gap to the eventual GC winner (0 = winner)",
)
fig3.update_traces(
    hovertemplate="<b>%{fullData.name}</b><br>Date: %{x}<br>Gap to winner: +%{y:.0f}s<extra></extra>"
)
fig3.update_layout(height=500, hovermode="x unified")
fig3 = style_fig(fig3, hovermode="x unified")
st.plotly_chart(fig3, use_container_width=True)
