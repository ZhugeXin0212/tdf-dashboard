"""
Task 3d -- Country Participation Analysis: number of teams per country,
number of riders per country.
"""

import plotly.express as px
import streamlit as st

from db import run_query
from style import insight_card, page_header, style_fig

page_header(
    "🌍 Country Participation Analysis",
    "Investigates how many teams and riders each country contributes, and highlights cross-national rosters.",
)

# ----------------------------------------------------------------------
# Teams per country
# ----------------------------------------------------------------------
teams_per_country_sql = """
    select c.country_name, c.country_code, count(*) as team_count
    from team t
    join country c on c.country_code = t.team_country_code
    group by c.country_name, c.country_code
    order by team_count desc
"""
teams_per_country = run_query(teams_per_country_sql)

riders_per_country_sql = """
    select c.country_name, c.country_code, count(*) as rider_count
    from rider r
    join country c on c.country_code = r.rider_country_code
    group by c.country_name, c.country_code
    order by rider_count desc
"""
riders_per_country = run_query(riders_per_country_sql)

top_team_country = teams_per_country.iloc[0]
top_rider_country = riders_per_country.iloc[0]
insight_card(
    f"<b>{top_team_country['country_name']}</b> fields the most teams "
    f"(<b>{int(top_team_country['team_count'])}</b>), while <b>{top_rider_country['country_name']}</b> "
    f"supplies the most riders overall (<b>{int(top_rider_country['rider_count'])}</b>)."
)

col1, col2 = st.columns(2)

with col1:
    st.subheader("🏢 Teams registered per country")
    fig1 = px.bar(
        teams_per_country,
        x="country_name",
        y="team_count",
        labels={"country_name": "Country", "team_count": "Number of teams"},
        color="team_count",
        color_continuous_scale="YlOrBr",
    )
    fig1.update_traces(hovertemplate="<b>%{x}</b><br>Teams: %{y}<extra></extra>")
    fig1.update_layout(xaxis_tickangle=-45, height=500, showlegend=False, coloraxis_showscale=False)
    fig1 = style_fig(fig1)
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("🚴 Riders by nationality")
    fig2 = px.bar(
        riders_per_country.head(15),
        x="country_name",
        y="rider_count",
        labels={"country_name": "Country", "rider_count": "Number of riders"},
        color="rider_count",
        color_continuous_scale="Greens",
    )
    fig2.update_traces(hovertemplate="<b>%{x}</b><br>Riders: %{y}<extra></extra>")
    fig2.update_layout(xaxis_tickangle=-45, height=500, showlegend=False, coloraxis_showscale=False)
    fig2 = style_fig(fig2)
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ----------------------------------------------------------------------
# World-map style choropleth of rider nationalities
# ----------------------------------------------------------------------
st.subheader("🗺️ Rider nationality world map")
st.caption(
    "Flat (equirectangular) projection, hover a country to lift it "
    "visually above its neighbors."
)
map_fig = px.choropleth(
    riders_per_country,
    locations="country_code",
    color="rider_count",
    hover_name="country_name",
    color_continuous_scale="YlOrRd",
    labels={"rider_count": "Riders"},
    projection="equirectangular",  # flat, horizontal world map
)
map_fig.update_traces(
    hovertemplate="<b>%{hovertext}</b><br>Riders: %{z}<extra></extra>",
    marker_line_width=0.4,
    marker_line_color="#FFFFFF",
)
# Soft basemap (muted tan land / pale blue ocean, thin white borders)
# instead of Plotly's default thick black coastlines -- that heavy
# black outline was the "ugly" look being flagged. Plotly choropleth
# has no native "lift this shape on hover" effect in pure
# Python/Streamlit (true elevation needs a JS-driven frontend like
# Dash); the bold dark hover label with a brand-colored border is the
# closest honest substitute for a hover "pop".
map_fig.update_geos(
    showland=True, landcolor="#EDEAE2",
    showocean=True, oceancolor="#EAF4FB",
    showcoastlines=True, coastlinecolor="#D9D4C7", coastlinewidth=0.5,
    showcountries=True, countrycolor="#FFFFFF", countrywidth=0.5,
    showlakes=True, lakecolor="#EAF4FB",
    showframe=False,
    bgcolor="rgba(0,0,0,0)",
)
map_fig.update_layout(
    height=500,
    margin=dict(l=0, r=0, t=20, b=0),
    plot_bgcolor="#FFFFFF",
    paper_bgcolor="#FFFFFF",
    font=dict(color="#1A1A1A"),
    hoverlabel=dict(
        bgcolor="#1A1A1A",
        font=dict(color="#FFFFFF", size=14, family="sans-serif"),
        bordercolor="#FFC72C",
        namelength=-1,
    ),
)
st.plotly_chart(map_fig, use_container_width=True)

st.divider()

# ----------------------------------------------------------------------
# National outcomes: best GC rank + wins/podiums achieved by each
# nation's riders (within the data we have -- GC only, since Points/
# KOM are simplified proxies on other pages).
# ----------------------------------------------------------------------
st.subheader("🥇 National GC Outcomes")
st.caption(
    "For each nation, the best General Classification rank achieved by "
    "any of its riders, plus how many wins (rank 1) and podiums (rank "
    "1-3) their riders collected."
)

national_outcomes_sql = """
    select
        c.country_name,
        min(a.rank) as best_gc_rank,
        sum(case when a.rank = 1 then 1 else 0 end) as wins,
        sum(case when a.rank <= 3 then 1 else 0 end) as podiums,
        count(*) as finishers
    from award_ind a
    join rider r on r.bib = a.bib
    join country c on c.country_code = r.rider_country_code
    group by c.country_name
    order by best_gc_rank asc
"""
national_outcomes = run_query(national_outcomes_sql)

winner_row = national_outcomes.iloc[0]
insight_card(
    f"<b>{winner_row['country_name']}</b> produced the GC winner "
    f"(best rank <b>{int(winner_row['best_gc_rank'])}</b>), with "
    f"<b>{int(national_outcomes['podiums'].sum())}</b> total podium finishes "
    f"across all nations."
)

st.dataframe(
    national_outcomes.head(15).rename(
        columns={
            "country_name": "Country",
            "best_gc_rank": "Best GC rank",
            "wins": "Wins (rank 1)",
            "podiums": "Podiums (rank 1-3)",
            "finishers": "Finishers",
        }
    ),
    hide_index=True,
    use_container_width=True,
    column_config={
        "Best GC rank": st.column_config.NumberColumn("Best GC rank", width="small"),
        "Wins (rank 1)": st.column_config.NumberColumn("Wins (rank 1)", width="small"),
        "Podiums (rank 1-3)": st.column_config.NumberColumn("Podiums (rank 1-3)", width="small"),
    },
)

st.divider()

# ----------------------------------------------------------------------
# Rider nationality vs team nationality -- drill into a specific country
# ----------------------------------------------------------------------
st.subheader("🔎 Explore a country's riders and teams")
countries = run_query("select country_code, country_name from country order by country_name")
selected_country = st.selectbox("Country", countries["country_name"])
code = countries.loc[countries["country_name"] == selected_country, "country_code"].iloc[0]

detail_sql = """
    select r.rider_name, r.bib, r.team, t.team_country_code
    from rider r
    join team t on t.team = r.team
    where r.rider_country_code = %(code)s
    order by r.rider_name
"""
detail_df = run_query(detail_sql, {"code": code})
detail_df["racing_for_foreign_team"] = detail_df["team_country_code"] != code

st.write(f"**{len(detail_df)} rider(s)** hold {selected_country} nationality.")
st.dataframe(
    detail_df.rename(
        columns={
            "rider_name": "Rider",
            "bib": "Bib",
            "team": "Team",
            "team_country_code": "Team's country",
            "racing_for_foreign_team": "Racing for a foreign team?",
        }
    ),
    hide_index=True,
    use_container_width=True,
    column_config={
        "Racing for a foreign team?": st.column_config.CheckboxColumn("Racing for a foreign team?"),
    },
)
