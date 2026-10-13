"""
Task 3a -- Drill-Down Analysis: explore results at different levels of
detail (stage -> rider / team).
"""

import plotly.express as px
import streamlit as st

from db import run_query
from style import insight_card, page_header, seconds_to_hms, style_fig

page_header("🔍 Stage Drill-Down Analysis", "Drill into results by stage, then by rider or team within that stage.")

# ----------------------------------------------------------------------
# Filters
# ----------------------------------------------------------------------
stages = run_query("select stage_id, day, type, length, start_location, finish_location from stage order by stage_id")
stages["label"] = stages.apply(
    lambda r: f"Stage {r.stage_id} ({r.day}) -- {r.start_location} to {r.finish_location} [{r.type}]",
    axis=1,
)

teams = run_query("select team from team order by team")

# Filters live at the top of the page (same row layout used on the All
# Riders / All Teams pages) instead of the sidebar.
f1, f2, f3 = st.columns([2, 1.5, 1])
with f1:
    stage_label = st.selectbox("Stage", stages["label"])
with f2:
    team_filter = st.multiselect("Team (optional)", teams["team"].tolist())
with f3:
    top_n = st.slider("Show top N finishers", min_value=5, max_value=100, value=20, step=5)

stage_row = stages.loc[stages["label"] == stage_label].iloc[0]
stage_id = int(stage_row["stage_id"])

st.subheader(f"🗺️ Stage {stage_id}: {stage_row['start_location']} → {stage_row['finish_location']}")
m1, m2, m3, m4 = st.columns(4)
m1.metric("📅 Date", str(stage_row["day"]))
m2.metric("🏔️ Type", stage_row["type"])
m3.metric("📏 Distance", f"{stage_row['length']} km")
m4.metric("🔢 Stage ID", stage_id)

# ----------------------------------------------------------------------
# Stage results table
# ----------------------------------------------------------------------
team_filter_sql = ""
params = {"stage_id": stage_id, "top_n": top_n}
if team_filter:
    team_filter_sql = "and r.team = any(%(teams)s)"
    params["teams"] = team_filter

result_sql = f"""
    select
        res.rank,
        r.bib,
        r.rider_name,
        r.team,
        res.time,
        res.bonus,
        res.penalty,
        (res.time - res.bonus + res.penalty) as adjusted_time
    from result res
    join stage s on s.day = res.day
    join rider r on r.bib = res.bib
    where s.stage_id = %(stage_id)s
    {team_filter_sql}
    order by res.rank
    limit %(top_n)s
"""
stage_results = run_query(result_sql, params)

if len(stage_results):
    winner_time = stage_results["adjusted_time"].min()
    insight_card(
        f"Stage winner finished in <b>{seconds_to_hms(winner_time)}</b>. "
        f"The gap column below shows how far behind each rider was."
    )
    stage_results["Gap"] = (stage_results["adjusted_time"] - winner_time).apply(
        lambda g: "—" if g == 0 else f"+{seconds_to_hms(g)}"
    )

st.dataframe(
    stage_results.rename(
        columns={
            "rank": "Rank",
            "bib": "Bib",
            "rider_name": "Rider",
            "team": "Team",
            "time": "Finish time (s)",
            "bonus": "Bonus (s)",
            "penalty": "Penalty (s)",
            "adjusted_time": "Adjusted time (s)",
        }
    ),
    hide_index=True,
    use_container_width=True,
    column_config={
        "Rank": st.column_config.NumberColumn("Rank", width="small"),
        "Adjusted time (s)": st.column_config.ProgressColumn(
            "Adjusted time (s)",
            min_value=float(stage_results["adjusted_time"].min()) if len(stage_results) else 0,
            max_value=float(stage_results["adjusted_time"].max()) if len(stage_results) else 1,
            format="%d s",
        ),
    },
)

st.divider()

# ----------------------------------------------------------------------
# Team-level aggregation for this stage
# ----------------------------------------------------------------------
st.subheader("🏢 Team performance on this stage")
st.caption("Average adjusted time per team among riders who finished this stage.")

team_agg_sql = """
    select
        r.team,
        avg(res.time - res.bonus + res.penalty) as avg_adjusted_time,
        count(*) as riders_finished
    from result res
    join stage s on s.day = res.day
    join rider r on r.bib = res.bib
    where s.stage_id = %(stage_id)s
    group by r.team
    order by avg_adjusted_time asc
"""
team_agg = run_query(team_agg_sql, {"stage_id": stage_id})

fig = px.bar(
    team_agg,
    x="team",
    y="avg_adjusted_time",
    labels={"team": "Team", "avg_adjusted_time": "Avg. adjusted time (s)"},
    title="Average adjusted time by team (lower is better)",
    color="avg_adjusted_time",
    color_continuous_scale="YlOrRd",
)
fig.update_traces(
    customdata=team_agg[["riders_finished"]].values,
    hovertemplate=(
        "<b>%{x}</b><br>"
        "Avg. adjusted time: %{y:.0f}s<br>"
        "Riders finished: %{customdata[0]}"
        "<extra></extra>"
    ),
)
fig.update_layout(xaxis_tickangle=-45, height=500, showlegend=False, coloraxis_showscale=False)
fig = style_fig(fig)
st.plotly_chart(fig, use_container_width=True)
