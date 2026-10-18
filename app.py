"""
Tour de France Dashboard -- router / entry point.

Run locally with:
    streamlit run app.py

This file is the single entry point. It defines the grouped sidebar
navigation (st.navigation with a dict of sections -> pages) and runs
page-independent setup (page config, global CSS) exactly once, before
routing to whichever view the user selected.

Pages live in views/ as plain Python modules (not the old pages/
auto-routing folder), each one just a script that renders its content
top-to-bottom -- st.navigation() executes the chosen one in place.
"""

import streamlit as st

from style import apply_global_style

st.set_page_config(
    page_title="Tour de France Dashboard",
    page_icon="🚴",
    layout="wide",
)
apply_global_style()

# ----------------------------------------------------------------------
# Grouped navigation: a dict maps section labels -> list of st.Page.
# This renders as a two-level sidebar (section header + its pages),
# instead of one long flat list of every page.
# ----------------------------------------------------------------------
pages = {
    "Overview": [
        st.Page("views/home.py", title="Home", icon="🏠", default=True),
    ],
    "Explore": [
        st.Page("views/all_riders.py", title="All Riders", icon="🚴"),
        st.Page("views/all_teams.py", title="All Teams", icon="🏢"),
    ],
    "Race Analysis": [
        st.Page("views/stage_drilldown.py", title="Stage Drill-Down", icon="🔍"),
        st.Page("views/classification_comparison.py", title="Classification Comparison", icon="🏆"),
        st.Page("views/aggregate_performance.py", title="Aggregate Performance", icon="📈"),
        st.Page("views/terrain_pace.py", title="Terrain & Pace", icon="⛰️"),
    ],
    "Geography": [
        st.Page("views/country_participation.py", title="Country Participation", icon="🌍"),
    ],
}

nav = st.navigation(pages)
nav.run()
