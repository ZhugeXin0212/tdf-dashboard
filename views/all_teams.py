"""
Detail page: full roster of all teams, with their riders and Best Team
ranking. Reached via the sidebar or by clicking "View all" on Home.
"""

import plotly.express as px
import streamlit as st

from db import run_query
from style import insight_card, page_header, seconds_to_hms, style_fig

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

sort_choice = st.radio(
    "Sort by", ["Roster depth (most riders first)", "Team name (A-Z)"], horizontal=True
)
if sort_choice.startswith("Roster"):
    filtered = filtered.sort_values("roster_size", ascending=False)
else:
    filtered = filtered.sort_values("team")

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
        "Riders": st.column_config.ProgressColumn(
            "Riders", min_value=0, max_value=int(teams_df["roster_size"].max()), format="%d"
        ),
        "Best Team rank": st.column_config.NumberColumn("Best Team rank", width="small"),
    },
)

st.divider()

# ----------------------------------------------------------------------
# Top-10 intensity by team: how many stage top-10 finishes each team
# racked up across the race, broken down by stage type.
# ----------------------------------------------------------------------
st.subheader("🔥 Top-10 Intensity by Team")
st.caption("Total stage top-10 finishes per team across all 21 stages, broken down by stage type.")

intensity_sql = """
    select r.team, s.type as stage_type, count(*) as top10_count
    from result res
    join stage s on s.day = res.day
    join rider r on r.bib = res.bib
    where res.rank <= 10
    group by r.team, s.type
"""
intensity_df = run_query(intensity_sql)
team_totals = intensity_df.groupby("team")["top10_count"].sum().sort_values(ascending=False)
top_team = team_totals.index[0]
insight_card(
    f"<b>{top_team}</b> leads all teams with <b>{int(team_totals.iloc[0])}</b> "
    f"total stage top-10 finishes across the race."
)

top_teams_order = team_totals.head(12).index.tolist()
intensity_plot_df = intensity_df[intensity_df["team"].isin(top_teams_order)]

intensity_fig = px.bar(
    intensity_plot_df,
    x="team",
    y="top10_count",
    color="stage_type",
    category_orders={"team": top_teams_order},
    labels={"team": "Team", "top10_count": "Top-10 finishes", "stage_type": "Stage type"},
    title="Stage top-10 finishes by team, broken down by terrain",
)
intensity_fig.update_traces(hovertemplate="<b>%{x}</b><br>%{fullData.name}: %{y}<extra></extra>")
intensity_fig.update_layout(xaxis_tickangle=-45, height=480, barmode="stack")
intensity_fig = style_fig(intensity_fig)
st.plotly_chart(intensity_fig, use_container_width=True)

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
