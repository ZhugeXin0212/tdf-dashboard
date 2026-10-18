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

# ----------------------------------------------------------------------
# Race-at-a-glance: the longest stage (with a one-click jump) and a
# compact catalogue of the individual time-trial (ITT) stages.
# ----------------------------------------------------------------------
longest_stage = stages.loc[stages["length"].idxmax()]

glance_col, itt_col = st.columns([1, 1.4], gap="medium")

with glance_col:
    with st.container(border=True):
        st.markdown("**📏 The longest day**")
        st.caption(
            f"Stage {int(longest_stage['stage_id'])} -- "
            f"{longest_stage['start_location']} → {longest_stage['finish_location']} "
            f"({longest_stage['length']} km, {longest_stage['type']})"
        )
        if st.button("Jump to this stage ↓", use_container_width=True):
            st.session_state["dd_stage_label"] = longest_stage["label"]

with itt_col:
    with st.container(border=True):
        st.markdown("**⏱️ Individual time-trial (ITT) stages**")
        itt_sql = """
            select
                s.stage_id, s.day, s.length,
                r.rider_name as winner, r.team as winner_team
            from stage s
            join result res on res.day = s.day and res.rank = 1
            join rider r on r.bib = res.bib
            where s.type = 'individual time-trial'
            order by s.stage_id
        """
        itt_df = run_query(itt_sql)
        st.dataframe(
            itt_df.rename(
                columns={
                    "stage_id": "Stage",
                    "day": "Date",
                    "length": "Distance (km)",
                    "winner": "Winner",
                    "winner_team": "Team",
                }
            ),
            hide_index=True,
            use_container_width=True,
            height=110,
        )

st.divider()

# ----------------------------------------------------------------------
# Filters live at the top of the page (same row layout used on the All
# Riders / All Teams pages) instead of the sidebar.
# ----------------------------------------------------------------------
if "dd_stage_label" not in st.session_state:
    st.session_state["dd_stage_label"] = stages["label"].iloc[0]

f1, f2, f3 = st.columns([2, 1.5, 1])
with f1:
    stage_label = st.selectbox("Stage", stages["label"], key="dd_stage_label")
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
# Team perspective on this stage: which squads placed riders in the
# top 10, and how many? (Not just "average time" -- a team can win the
# day on strength in numbers even without the single fastest rider.)
# ----------------------------------------------------------------------
st.subheader("🏢 Which teams made the top 10 today?")
st.caption("Counts how many riders from each team finished in the top 10 of this stage.")

team_top10_sql = """
    select r.team, count(*) as riders_in_top10
    from result res
    join stage s on s.day = res.day
    join rider r on r.bib = res.bib
    where s.stage_id = %(stage_id)s and res.rank <= 10
    group by r.team
    order by riders_in_top10 desc
"""
team_top10_stage = run_query(team_top10_sql, {"stage_id": stage_id})

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

tcol1, tcol2 = st.columns(2, gap="medium")

with tcol1:
    fig_top10 = px.bar(
        team_top10_stage,
        x="team",
        y="riders_in_top10",
        labels={"team": "Team", "riders_in_top10": "Riders in top 10"},
        title="Riders placed in the stage top 10, by team",
        color="riders_in_top10",
        color_continuous_scale="YlOrBr",
    )
    fig_top10.update_traces(hovertemplate="<b>%{x}</b><br>Riders in top 10: %{y}<extra></extra>")
    fig_top10.update_layout(xaxis_tickangle=-45, height=450, showlegend=False, coloraxis_showscale=False)
    fig_top10 = style_fig(fig_top10)
    st.plotly_chart(fig_top10, use_container_width=True)

with tcol2:
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
    fig.update_layout(xaxis_tickangle=-45, height=450, showlegend=False, coloraxis_showscale=False)
    fig = style_fig(fig)
    st.plotly_chart(fig, use_container_width=True)
