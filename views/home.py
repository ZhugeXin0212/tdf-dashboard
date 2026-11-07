"""
Executive Summary -- the one-screen answer for a decision maker.

Pattern: hero KPIs -> six headline insights (each computed live from the
database and linked to the page holding the evidence) -> two "race at a
glance" visuals -> reading guide. Registered via st.navigation in app.py.
"""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import analytics as A
from style import (
    short_team,
    STAGE_TYPE_COLORS,
    business_question,
    finding_card,
    fmt_gap,
    kpi_row,
    page_header,
    section,
    style_fig,
)

page_header(
    "🚴 Tour de France — Performance Intelligence Dashboard",
    "From raw stage results to decisions: who won, where the race was decided, "
    "and what teams, organisers and national federations should take away.",
)
business_question(
    "What decided this Tour de France, and what does it mean for the people who plan the next one?",
    "Audience: team sports directors (strategy & recruitment), race organisers (route design), "
    "national federations & sponsors (talent investment).",
)

stg = A.stages()
riders = A.riders()
gcf = A.gc_final()
winner, runner = A.winner_and_runner_up()
lost = A.time_lost_vs(int(winner["bib"]), int(runner["bib"]))
terrain = A.margin_by_terrain(lost).set_index("type_label")
margin = int(lost["lost"].sum())
key_stage = lost.sort_values("lost", ascending=False).iloc[0]
sc = A.team_scorecard()
best_team = sc.iloc[0]
winner_team = sc.set_index("team").loc[winner["team"]]
rho_top10 = A.spearman(sc["top10_finishes"], -sc["best_team_rank"])
rho_wins = A.spearman(sc["stage_wins"], -sc["best_team_rank"])
nat = A.nation_scorecard()
host = nat.iloc[0]
efficient = nat[nat["riders"] >= 3].sort_values("top10_per_rider", ascending=False).iloc[0]
exits = riders[riders["exit_stage"].notna()].merge(
    stg[["stage_id", "type_label"]], left_on="exit_stage", right_on="stage_id"
)
mtn_exit_share = (exits["type_label"] == "Mountain").mean()
mtn_stage_share = (stg["type_label"] == "Mountain").mean()
leaders = riders[riders["is_leader"]]
leaders_out = int(leaders["gc_rank"].isna().sum())
best_by_team = gcf.groupby("team")["gc_rank"].min()
lead_rank = leaders.set_index("team")["gc_rank"]
plan_b = int(((best_by_team.reindex(lead_rank.index) < lead_rank) | lead_rank.isna()).sum())
finish_rate = riders["gc_rank"].notna().mean()

# ----------------------------------------------------------------------
# Hero KPIs
# ----------------------------------------------------------------------
kpi_row([
    ("🟡 GC winner", winner["rider_name"], short_team(winner["team"])),
    ("⏱️ Winning margin", fmt_gap(margin).lstrip("+"), f"over {runner['rider_name']}"),
    ("🎯 Decisive stage", f"Stage {int(key_stage['stage_id'])}",
     f"{key_stage['lost']}s = {key_stage['lost'] / margin:.0%} of the margin ({key_stage['type_label']})"),
    ("🏆 Best Team", short_team(best_team["team"]), f"only {int(best_team['stage_wins'])} stage wins"),
    ("🏁 Finish rate", f"{finish_rate:.0%}", f"{int(riders['gc_rank'].isna().sum())} of {len(riders)} riders exited"),
    ("🗺️ Route", f"{len(stg)} stages · {stg['length'].sum():,.0f} km",
     " · ".join(f"{(stg.type_label == t).sum()} {t}" for t in ["Flat", "Hilly", "Mountain", "ITT"])),
])

# ----------------------------------------------------------------------
# Six headline insights
# ----------------------------------------------------------------------
section("★", "Six things a decision maker should know", "live from database")

mtn, itt, flat = terrain.loc["Mountain"], terrain.loc["ITT"], terrain.loc["Flat"]
cards = [
    dict(
        kicker="Where the Tour was won",
        value=f"{mtn['share']:.0%} mountains · {itt['share']:.0%} ITT",
        text=f"Of the {margin}s winning margin, flat stages contributed "
        f"<b>{int(flat['seconds'])}s</b>. GC is decided on climbs and against the clock.",
        accent="#D32F2F",
        page="views/race_story.py",
    ),
    dict(
        kicker="Most time-efficient battleground",
        value=f"ITT: {itt['sec_per_100km']:.0f}s / 100 km",
        text=f"vs <b>{mtn['sec_per_100km']:.0f}s</b> per 100 km in the mountains — only "
        f"{itt['km']:.0f} km of time-trial produced {int(itt['seconds'])}s of the gap.",
        accent="#1565C0",
        page="views/race_story.py",
    ),
    dict(
        kicker="Depth beats star power",
        value=short_team(best_team['team']),
        text=f"won Best Team with {int(best_team['finishers'])}/{int(best_team['roster'])} finishers and "
        f"{int(best_team['top10_finishes'])} stage top-10s, ahead of the GC winner's team "
        f"({int(winner_team['stage_wins'])} stage wins). Best-Team rank correlates with stage top-10s "
        f"(ρ={rho_top10:.2f}) far more than with stage wins (ρ={rho_wins:.2f}).",
        accent="#2E7D32",
        page="views/team_strategy.py",
    ),
    dict(
        kicker="Plan B is not optional",
        value=f"{leaders_out} of {len(leaders)} leaders out",
        text=f"designated team leaders failed to reach Paris, and in <b>{plan_b}</b> of {len(leaders)} squads the "
        "team's best GC finisher was <i>not</i> the designated leader. Rosters need a credible second option.",
        accent="#6A1B9A",
        page="views/team_strategy.py",
    ),
    dict(
        kicker="Volume ≠ value (nations)",
        value=f"{host['rider_country']} {int(host['riders'])} riders",
        text=f"is the largest nation but its best GC was <b>{int(host['best_gc'])}</b>; "
        f"{efficient['rider_country']} converted {int(efficient['riders'])} riders into "
        f"<b>{int(efficient['stage_top10'])}</b> stage top-10s ({efficient['top10_per_rider']:.1f} per rider).",
        accent="#00897B",
        page="views/country_participation.py",
    ),
    dict(
        kicker="Mountains also drive attrition",
        value=f"{mtn_exit_share:.0%} of exits",
        text=f"happened at mountain stages, which are only {mtn_stage_share:.0%} of the route — "
        "the same stages that decide GC are where squads lose riders.",
        accent="#EF6C00",
        page="views/stage_drilldown.py",
    ),
]
for row in (cards[:3], cards[3:]):
    cols = st.columns(3, gap="medium")
    for col, c in zip(cols, row):
        with col:
            finding_card(c["kicker"], c["value"], c["text"], c["accent"])
            st.page_link(c["page"], label="See the evidence →")

# ----------------------------------------------------------------------
# Race at a glance
# ----------------------------------------------------------------------
section("◎", "Race at a glance")
left, right = st.columns([1.5, 1], gap="medium")

with left:
    with st.container(border=True):
        g = A.gc_daily()
        top5 = gcf.head(5)["bib"].tolist()
        gd = g[g["bib"].isin(top5)].copy()
        # gap to the eventual winner (not to the day's leader) makes the
        # story of how the final margin was built easy to read
        wcum = gd[gd["bib"] == winner["bib"]].set_index("stage_id")["cumulative_time"]
        gd["gap_to_winner_min"] = (gd["cumulative_time"] - gd["stage_id"].map(wcum)) / 60
        fig = px.line(
            gd, x="stage_id", y="gap_to_winner_min", color="rider_name", markers=True,
            labels={"stage_id": "Stage", "gap_to_winner_min": "Minutes behind eventual winner", "rider_name": "Rider"},
            title="How the final top 5 drifted away from the winner",
        )
        for _, s in stg[stg["type_label"].isin(["Mountain", "ITT"])].iterrows():
            fig.add_vrect(x0=s.stage_id - 0.5, x1=s.stage_id + 0.5, layer="below", line_width=0,
                          fillcolor=STAGE_TYPE_COLORS[s.type_label], opacity=0.08)
        fig.update_traces(hovertemplate="<b>%{fullData.name}</b><br>Stage %{x}: %{y:.1f} min<extra></extra>")
        fig.update_layout(height=380, xaxis=dict(dtick=1, range=[0.5, len(stg) + 0.5]))
        st.plotly_chart(style_fig(fig, hovermode="x unified"), use_container_width=True)
        st.caption("Red bands = Mountain stages, blue bands = ITTs. Lines bend upward almost only inside the bands.")

with right:
    with st.container(border=True):
        tdf = terrain.reset_index()
        fig2 = go.Figure(
            go.Bar(
                x=tdf["type_label"], y=tdf["seconds"],
                marker_color=[STAGE_TYPE_COLORS[t] for t in tdf["type_label"]],
                text=[f"{s:.0f}s<br>{sh:.0%}" for s, sh in zip(tdf["seconds"], tdf["share"])],
                textposition="outside",
                customdata=tdf[["km", "sec_per_100km"]].fillna(0).values,
                hovertemplate="<b>%{x}</b><br>Gap built: %{y:.0f}s<br>Km raced: %{customdata[0]:.0f}"
                "<br>Seconds per 100 km: %{customdata[1]:.0f}<extra></extra>",
            )
        )
        fig2.update_layout(
            title=f"Where the {margin}s margin came from",
            yaxis_title=f"Seconds {winner['rider_name'].split()[-1]} gained",
            height=380, showlegend=False,
        )
        fig2.update_yaxes(range=[0, tdf["seconds"].max() * 1.25])
        st.plotly_chart(style_fig(fig2), use_container_width=True)
        st.caption(f"Winner vs runner-up ({runner['rider_name']}), summed by stage type.")

# ----------------------------------------------------------------------
# Reading guide
# ----------------------------------------------------------------------
section("→", "How to read this dashboard")
g1, g2, g3 = st.columns(3, gap="medium")
with g1:
    with st.container(border=True):
        st.markdown("**1 · Race Outcome** — *what happened & where*")
        st.page_link("views/race_story.py", label="Race Storyline: GC timeline, margin decomposition, counterfactuals", icon="📈")
        st.page_link("views/stage_drilldown.py", label="Stage Analysis: decisive stages, attrition, any stage in focus", icon="🗺️")
with g2:
    with st.container(border=True):
        st.markdown("**2 · Performance Drivers** — *who & why*")
        st.page_link("views/classification_comparison.py", label="Riders & Classifications: GC, Points, KOM, Young, consistency", icon="🏆")
        st.page_link("views/terrain_pace.py", label="Terrain & Rider Profiles: climber vs time-trialist map, pace", icon="⛰️")
with g3:
    with st.container(border=True):
        st.markdown("**3 · Stakeholder Views** — *so what for whom*")
        st.page_link("views/team_strategy.py", label="Team Strategy: depth vs stars, time burden, leader risk", icon="🏢")
        st.page_link("views/country_participation.py", label="Nations: participation vs conversion", icon="🌍")
