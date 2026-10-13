"""
Tour de France Dashboard -- Home / Overview page.

Registered as a page via st.navigation() in app.py (the router). Do not
call st.set_page_config() or apply_global_style() here -- both are
centralized once in app.py.
"""

import plotly.express as px
import streamlit as st

from db import run_query
from style import insight_card, page_header, seconds_to_hms, style_fig

page_header(
    "🚴 Tour de France 2023 — Analytics Dashboard",
    "BT5110 Project · Task 3 OLAP Dashboard — covers all 21 stages, 184 registered riders, and 23 teams.",
)

# ----------------------------------------------------------------------
# Top-level KPI row. Each card links to a detail page -- click through
# to see the full underlying list (Power BI "card + drill" pattern).
# ----------------------------------------------------------------------
kpi_sql = """
    select
        (select count(*) from rider)                         as total_riders,
        (select count(*) from team)                           as total_teams,
        (select count(*) from country)                        as total_countries,
        (select count(*) from stage)                          as total_stages,
        (select count(*) from exit_record)                    as total_exits,
        (select count(*) from award_ind)                      as finishers
"""
kpi = run_query(kpi_sql).iloc[0]
finish_rate = kpi["finishers"] / kpi["total_riders"] * 100

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric("🚴 Riders", int(kpi["total_riders"]))
    st.page_link("views/all_riders.py", label="View all →", icon="🚴")

with col2:
    st.metric("🏢 Teams", int(kpi["total_teams"]))
    st.page_link("views/all_teams.py", label="View all →", icon="🏢")

with col3:
    st.metric("🌍 Countries", int(kpi["total_countries"]))
    st.page_link("views/country_participation.py", label="Explore →", icon="🌍")

with col4:
    st.metric("🗺️ Stages", int(kpi["total_stages"]))
    st.page_link("views/stage_drilldown.py", label="Explore →", icon="🗺️")

with col5:
    st.metric("🏁 Finishers", int(kpi["finishers"]))
    st.page_link("views/all_riders.py", label="View all →", icon="🏁")

with col6:
    st.metric("🚫 Withdrawals", int(kpi["total_exits"]))
    st.page_link("views/all_riders.py", label="View all →", icon="🚫")

insight_card(
    f"<b>{finish_rate:.0f}%</b> of starters completed all 21 stages. "
    f"The remaining <b>{int(kpi['total_exits'])}</b> riders withdrew (DNS/DNF) "
    "at some point — click a KPI card above to see the full list."
)

st.divider()

# ----------------------------------------------------------------------
# General Classification podium
# ----------------------------------------------------------------------
left, right = st.columns(2)

with left:
    with st.container(border=True):
        st.subheader("🟡 General Classification — Top 10")
        gc_sql = """
            select
                a.rank,
                r.rider_name,
                r.team,
                a.adjusted_time,
                a.adjusted_time - (select min(adjusted_time) from award_ind) as gap_to_leader
            from award_ind a
            join rider r on r.bib = a.bib
            order by a.rank
            limit 10
        """
        gc_top10 = run_query(gc_sql)
        gc_top10["Total time"] = gc_top10["adjusted_time"].apply(seconds_to_hms)
        gc_top10["Gap"] = gc_top10["gap_to_leader"].apply(lambda g: "—" if g == 0 else f"+{seconds_to_hms(g)}")
        st.dataframe(
            gc_top10[["rank", "rider_name", "team", "Total time", "Gap"]].rename(
                columns={"rank": "Rank", "rider_name": "Rider", "team": "Team"}
            ),
            hide_index=True,
            use_container_width=True,
            column_config={"Rank": st.column_config.NumberColumn("Rank", width="small")},
        )
        st.page_link("views/classification_comparison.py", label="View full classification →", icon="🏆")

with right:
    with st.container(border=True):
        st.subheader("🏆 Best Team — Top 10")
        team_sql = """
            select
                rank,
                team,
                aggregate_time,
                aggregate_time - (select min(aggregate_time) from award_team) as gap_to_leader
            from award_team
            order by rank
            limit 10
        """
        team_top10 = run_query(team_sql)
        team_top10["Aggregate time"] = team_top10["aggregate_time"].apply(seconds_to_hms)
        team_top10["Gap"] = team_top10["gap_to_leader"].apply(lambda g: "—" if g == 0 else f"+{seconds_to_hms(g)}")
        st.dataframe(
            team_top10[["rank", "team", "Aggregate time", "Gap"]].rename(columns={"rank": "Rank", "team": "Team"}),
            hide_index=True,
            use_container_width=True,
            column_config={"Rank": st.column_config.NumberColumn("Rank", width="small")},
        )
        st.page_link("views/all_teams.py", label="View all teams →", icon="🏢")

st.divider()

# ----------------------------------------------------------------------
# Nationality mix: rider nationality vs team nationality.
# Redesigned as two matching bordered cards; legend removed in favor of
# outside slice labels (avoids the legend/chart overlap seen before),
# and the right card is filled with a "top mismatches" list so neither
# card is mostly empty space.
# ----------------------------------------------------------------------
st.subheader("🌐 Rider Nationality vs Team Nationality")
st.caption(
    "Each rider's personal nationality does not have to match the "
    "country their team is registered under — e.g. a French team can "
    "field a German rider."
)

mix_sql = """
    select
        rc.country_name as rider_country_name,
        tc.country_name as team_country_name,
        r.rider_country_code,
        t.team_country_code,
        count(*) as rider_count
    from rider r
    join team t on t.team = r.team
    left join country rc on rc.country_code = r.rider_country_code
    left join country tc on tc.country_code = t.team_country_code
    where r.rider_country_code is not null
    group by rc.country_name, tc.country_name, r.rider_country_code, t.team_country_code
    order by rider_count desc
"""
mix_df = run_query(mix_sql)
mix_df["same_nationality"] = mix_df["rider_country_code"] == mix_df["team_country_code"]
same_count = int(mix_df.loc[mix_df["same_nationality"], "rider_count"].sum())
diff_count = int(mix_df.loc[~mix_df["same_nationality"], "rider_count"].sum())
total = same_count + diff_count

pie_col, spacer_col, note_col = st.columns([2, 0.2, 3], gap="small")

with pie_col:
    with st.container(border=True):
        fig = px.pie(
            names=["Rides for home-nation team", "Rides for foreign team"],
            values=[same_count, diff_count],
            hole=0.5,
            color_discrete_sequence=["#E6A817", "#1565C0"],
        )
        # Labels live outside the pie with auto leader-lines back to each
        # slice -- no text crammed (and rotated) inside the ring, and no
        # center annotation. Full detail (exact counts) surfaces on hover.
        fig.update_traces(
            textinfo="percent",
            textposition="outside",
            textfont_size=14,
            hovertemplate="<b>%{label}</b><br>Riders: %{value}<br>Share: %{percent}<extra></extra>",
        )
        fig.update_layout(
            showlegend=False,
            margin=dict(t=30, b=30, l=70, r=70),
            height=340,
        )
        fig = style_fig(fig)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("🟡 Home-nation team · 🔵 Foreign team — hover a slice for exact counts.")

with note_col:
    with st.container(border=True):
        st.metric(
            "Riders racing outside own nationality",
            f"{diff_count} / {total}",
            f"{diff_count / total * 100:.1f}%",
        )
        st.markdown("**Top cross-national pairings**")
        top_mismatch = mix_df.loc[~mix_df["same_nationality"]].head(5)
        for _, row in top_mismatch.iterrows():
            st.markdown(
                f"- {row['rider_country_name']} riders → **{row['team_country_name']}** teams: "
                f"**{int(row['rider_count'])}** rider(s)"
            )

st.divider()
st.caption(
    "Navigate using the sidebar to explore stage-by-stage drill-down, "
    "classification comparisons, cumulative performance trends, and "
    "country participation analysis."
)
