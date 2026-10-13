"""
Detail page: full roster of all teams, with their riders and Best Team
ranking. Reached via the sidebar or by clicking "View all" on Home.
"""

import streamlit as st

from db import run_query
from style import page_header, seconds_to_hms

page_header("🏢 All Teams", "Every registered team, its nationality, leader, and Best Team ranking.")

teams_sql = """
    select
        t.team,
        t.team_country_code,
        c.country_name as team_country_name,
        t.leader_bib,
        lr.rider_name as leader_name,
        at.rank as best_team_rank,
        at.aggregate_time,
        count(r.bib) as roster_size
    from team t
    left join country c on c.country_code = t.team_country_code
    left join rider lr on lr.bib = t.leader_bib
    left join award_team at on at.team = t.team
    left join rider r on r.team = t.team
    group by t.team, t.team_country_code, c.country_name, t.leader_bib, lr.rider_name, at.rank, at.aggregate_time
    order by t.team
"""
teams_df = run_query(teams_sql)

team_options = sorted(teams_df["team"].unique().tolist())
selected_teams = st.multiselect(
    "🔎 Search team (type to filter, click to select)",
    team_options,
    default=[],
    placeholder="Type a team name…",
)
filtered = teams_df.copy()
if selected_teams:
    filtered = filtered[filtered["team"].isin(selected_teams)]

filtered = filtered.copy()
filtered["Aggregate time"] = filtered["aggregate_time"].apply(seconds_to_hms)

st.caption(f"Showing **{len(filtered)}** of **{len(teams_df)}** teams.")

st.dataframe(
    filtered[
        ["team", "team_country_name", "leader_name", "roster_size", "best_team_rank", "Aggregate time"]
    ].rename(
        columns={
            "team": "Team",
            "team_country_name": "Country",
            "leader_name": "Team leader",
            "roster_size": "Riders",
            "best_team_rank": "Best Team rank",
        }
    ),
    hide_index=True,
    use_container_width=True,
    height=600,
    column_config={
        "Best Team rank": st.column_config.NumberColumn("Best Team rank", width="small"),
    },
)

st.divider()
st.subheader("🔎 Team roster")
selected_team = st.selectbox("Select a team to view its full roster", sorted(teams_df["team"].tolist()))
roster_sql = """
    select r.bib, r.rider_name, r.dob, c.country_name as nationality
    from rider r
    left join country c on c.country_code = r.rider_country_code
    where r.team = %(team)s
    order by r.bib
"""
roster_df = run_query(roster_sql, {"team": selected_team})
st.dataframe(
    roster_df.rename(columns={"bib": "Bib", "rider_name": "Rider", "dob": "Date of birth", "nationality": "Nationality"}),
    hide_index=True,
    use_container_width=True,
)
