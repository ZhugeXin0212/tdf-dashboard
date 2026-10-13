"""
Detail page: full roster of all registered riders.

Reached either via the sidebar navigation or by clicking a KPI card /
"View all" link on the Home page. Supports search and status filtering
so it works as a genuine drill-down target, not just a dump of rows.
"""

import streamlit as st

from db import run_query
from style import page_header

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
