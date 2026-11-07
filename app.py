"""
Tour de France Dashboard -- router / entry point.

Run locally with:
    streamlit run app.py

The navigation follows a business-dashboard storyline rather than a
list of tables:

    Executive Summary  ->  1 Race Outcome (how & where the race was won)
                       ->  2 Performance Drivers (stages, riders, terrain)
                       ->  3 Stakeholder Views (teams, nations)
                       ->  Reference (directories, requirement map)

Every analysis page follows the same pattern:
    business question -> headline findings -> evidence (charts with
    drill-down) -> "So what?" implications.
"""

import streamlit as st

from style import apply_global_style

st.set_page_config(
    page_title="Tour de France Dashboard",
    page_icon="🚴",
    layout="wide",
)
apply_global_style()

pages = {
    "Executive Summary": [
        st.Page("views/home.py", title="Executive Summary", icon="🏠", default=True),
    ],
    "1 · Race Outcome": [
        st.Page("views/race_story.py", title="Race Storyline", icon="📈"),
        st.Page("views/stage_drilldown.py", title="Stage Analysis", icon="🗺️"),
    ],
    "2 · Performance Drivers": [
        st.Page("views/classification_comparison.py", title="Riders & Classifications", icon="🏆"),
        st.Page("views/terrain_pace.py", title="Terrain & Rider Profiles", icon="⛰️"),
    ],
    "3 · Stakeholder Views": [
        st.Page("views/team_strategy.py", title="Team Strategy", icon="🏢"),
        st.Page("views/country_participation.py", title="Nations", icon="🌍"),
    ],
    "Reference": [
        st.Page("views/all_riders.py", title="Rider Directory & Profile", icon="🚴"),
        st.Page("views/all_teams.py", title="Team Directory", icon="📋"),
        st.Page("views/requirements_map.py", title="Requirement Map & Method", icon="🧭"),
    ],
}

nav = st.navigation(pages)
nav.run()
