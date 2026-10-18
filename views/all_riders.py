"""
Detail page: full roster of all registered riders.

Reached either via the sidebar navigation or by clicking a KPI card /
"View all" link on the Home page. Supports search and status filtering
so it works as a genuine drill-down target, not just a dump of rows.
"""

import plotly.express as px
import streamlit as st

from db import run_query
from style import page_header, style_fig

page_header("🚴 All Riders", "Full roster of every registered rider, with search and status filters.")

riders_sql = """
    select
        r.bib,
        r.rider_name,
        r.dob,
        r.team,
        r.rider_country_code,
        c.country_name as rider_country_name,
        case when a.bib is not null then 'Finished' else 'Withdrawn / DNF' end as status,
        a.rank as gc_rank,
        a.adjusted_time,
        e.reason as exit_reason,
        e.stage_id as exit_stage
    from rider r
    left join country c on c.country_code = r.rider_country_code
    left join award_ind a on a.bib = r.bib
    left join exit_record e on e.bib = r.bib
    order by r.bib
"""
riders_df = run_query(riders_sql)

# Pre-fill the status filter if the user clicked a KPI card on Home
# that set this via session_state before switching pages.
default_status = st.session_state.pop("rider_status_filter", "All")

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    # Type-ahead dropdown: start typing to filter the option list live,
    # click a match to add it, click the "x" on a pill to clear it --
    # same interaction pattern as the rider selector on Classification
    # Comparison. Leaving it empty means "no name filter".
    rider_options = sorted(riders_df["rider_name"].unique().tolist())
    selected_riders = st.multiselect(
        "🔎 Search rider (type to filter, click to select)",
        rider_options,
        default=[],
        placeholder="Type a rider name…",
    )
with col2:
    status_filter = st.selectbox(
        "Status", ["All", "Finished", "Withdrawn"],
        index=["All", "Finished", "Withdrawn"].index(default_status) if default_status in ["All", "Finished", "Withdrawn"] else 0,
    )
with col3:
    teams = ["All teams"] + sorted(riders_df["team"].unique().tolist())
    team_filter = st.selectbox("Team", teams)

filtered = riders_df.copy()
if selected_riders:
    filtered = filtered[filtered["rider_name"].isin(selected_riders)]
if status_filter == "Finished":
    filtered = filtered[filtered["status"] == "Finished"]
elif status_filter == "Withdrawn":
    filtered = filtered[filtered["status"] == "Withdrawn / DNF"]
if team_filter != "All teams":
    filtered = filtered[filtered["team"] == team_filter]

st.caption(f"Showing **{len(filtered)}** of **{len(riders_df)}** riders.")

st.dataframe(
    filtered[
        ["bib", "rider_name", "dob", "team", "rider_country_name", "status", "gc_rank", "exit_reason", "exit_stage"]
    ].rename(
        columns={
            "bib": "Bib",
            "rider_name": "Rider",
            "dob": "Date of birth",
            "team": "Team",
            "rider_country_name": "Nationality",
            "status": "Status",
            "gc_rank": "GC rank",
            "exit_reason": "Exit reason",
            "exit_stage": "Exit stage",
        }
    ),
    hide_index=True,
    use_container_width=True,
    height=600,
)

st.divider()

# ----------------------------------------------------------------------
# Top-10 regulars: riders who most often finished in a stage's top 10,
# with a drill-down into exactly which stages contributed.
# ----------------------------------------------------------------------
st.subheader("🔥 Top-10 Regulars")
st.caption("Riders who most often finished in a stage's top 10, across all 21 stages.")

regulars_sql = """
    select r.bib, r.rider_name, r.team, count(*) as top10_count
    from result res
    join rider r on r.bib = res.bib
    where res.rank <= 10
    group by r.bib, r.rider_name, r.team
    order by top10_count desc
    limit 15
"""
regulars_df = run_query(regulars_sql)

rcol1, rcol2 = st.columns([1.2, 1], gap="medium")

with rcol1:
    reg_fig = px.bar(
        regulars_df,
        x="top10_count",
        y="rider_name",
        orientation="h",
        color="top10_count",
        color_continuous_scale="YlOrBr",
        labels={"top10_count": "Stage top-10 finishes", "rider_name": "Rider"},
        title="Most frequent stage top-10 finishers",
    )
    reg_fig.update_traces(
        customdata=regulars_df[["team"]].values,
        hovertemplate="<b>%{y}</b> (%{customdata[0]})<br>Top-10 finishes: %{x}<extra></extra>",
    )
    reg_fig.update_layout(height=480, yaxis=dict(autorange="reversed"), coloraxis_showscale=False)
    reg_fig = style_fig(reg_fig)
    st.plotly_chart(reg_fig, use_container_width=True)

with rcol2:
    st.markdown("**Drill into a rider's contributing stages**")
    regular_pick = st.selectbox("Rider", regulars_df["rider_name"].tolist(), key="regulars_pick")
    pick_bib = regulars_df.loc[regulars_df["rider_name"] == regular_pick, "bib"].iloc[0]
    contributing_sql = """
        select s.stage_id, s.day, s.type, res.rank
        from result res
        join stage s on s.day = res.day
        where res.bib = %(bib)s and res.rank <= 10
        order by s.stage_id
    """
    contributing_df = run_query(contributing_sql, {"bib": int(pick_bib)})
    st.dataframe(
        contributing_df.rename(
            columns={"stage_id": "Stage", "day": "Date", "type": "Stage type", "rank": "Rank"}
        ),
        hide_index=True,
        use_container_width=True,
        height=400,
    )
