"""
3 · Stakeholder Views -- Nations.

Task 3d (number of teams and riders per country) plus suggested prompts
E8 (participation by nation, opening the roll-up to riders and teams of
a chosen country) and E9 (national outcomes: best GC rank, stage
wins/podiums, with a pathway back to stages and athletes). Adds the
analysis a federation or sponsor needs: does participation convert into
results?
"""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import analytics as A
from style import (
    business_question,
    finding_card,
    fmt_gap,
    insight_card,
    page_header,
    section,
    so_what,
    style_fig,
)

page_header("🌍 Nations", "Who supplies the peloton — and which nations turn participation into results.")
business_question(
    "Which nations are most present in the race, and which convert their riders into results most efficiently?",
    "Use: national federations (talent investment), sponsors & broadcasters (market relevance), organisers (wildcards).",
)

nat = A.nation_scorecard()
riders = A.riders()
res = A.results()
teams = A.teams()

host = nat.iloc[0]
total_riders = int(nat["riders"].sum())
total_top10 = int(nat["stage_top10"].sum())
eff = nat[nat["riders"] >= 3].sort_values("top10_per_rider", ascending=False).iloc[0]
cross = riders.dropna(subset=["rider_country_code"])
cross_share = (cross["rider_country_code"] != cross["team_country_code"]).mean()
team_nations = teams["team_country_code"].nunique()

# ----------------------------------------------------------------------
# 1. Participation (Task 3d, E8)
# ----------------------------------------------------------------------
section("1", "Participation — teams and riders per country", "Task 3d · E8")
k = st.columns(4)
with k[0]:
    finding_card("Rider nationalities", f"{len(nat)}", f"vs only {team_nations} team-registration countries", "#1565C0")
with k[1]:
    finding_card("Largest nation", f"{host['rider_country']}", f"{int(host['riders'])} riders "
                 f"({host['riders'] / total_riders:.0%} of the peloton) · {int(host['teams'])} teams", "#E6A817")
with k[2]:
    finding_card("Riding for a foreign team", f"{cross_share:.0%}", "of riders — talent markets are international", "#6A1B9A")
with k[3]:
    top5_share = nat.head(5)["riders"].sum() / total_riders
    finding_card("Top-5 nations' share", f"{top5_share:.0%}", "of all riders — participation is concentrated in Europe", "#00897B")

c1, c2 = st.columns([1.3, 1], gap="medium")
with c1:
    show = nat.head(15).copy()
    fig = go.Figure()
    fig.add_bar(x=show["rider_country_code"], y=show["riders"], name="Riders", marker_color="#1565C0",
                customdata=show[["rider_country"]].values,
                hovertemplate="<b>%{customdata[0]}</b><br>Riders: %{y}<extra></extra>")
    fig.add_bar(x=show["rider_country_code"], y=show["teams"], name="Teams registered", marker_color="#E6A817",
                customdata=show[["rider_country"]].values,
                hovertemplate="<b>%{customdata[0]}</b><br>Teams: %{y}<extra></extra>")
    fig.update_layout(title="Riders by nationality vs teams registered (top 15 nations)", barmode="group",
                      height=430, legend=dict(orientation="h", y=1.1), xaxis_title="Nation (ISO code)")
    st.plotly_chart(style_fig(fig), use_container_width=True)
with c2:
    tab_tree, tab_map = st.tabs(["Volume × conversion", "World map"])
    with tab_tree:
        tree = px.treemap(nat, path=[px.Constant("All riders"), "rider_country"], values="riders",
                          color="top10_per_rider", color_continuous_scale="RdYlGn",
                          color_continuous_midpoint=float(nat["stage_top10"].sum() / nat["riders"].sum()),
                          custom_data=["stage_top10", "top10_per_rider"])
        tree.update_traces(hovertemplate="<b>%{label}</b><br>Riders: %{value}<br>Stage top-10s: %{customdata[0]}"
                           "<br>Per rider: %{customdata[1]:.2f}<extra></extra>")
        tree.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), coloraxis_colorbar=dict(title="Top-10s / rider"))
        st.plotly_chart(tree, use_container_width=True)
        st.caption("Box size = riders; colour = stage top-10s per rider (green = converts above average).")
    with tab_map:
        map_fig = px.choropleth(nat, locations="rider_country_code", color="riders", hover_name="rider_country",
                                color_continuous_scale="YlOrRd", labels={"riders": "Riders"}, projection="natural earth")
        map_fig.update_traces(hovertemplate="<b>%{hovertext}</b><br>Riders: %{z}<extra></extra>",
                              marker_line_width=0.4, marker_line_color="#FFFFFF")
        map_fig.update_geos(showland=True, landcolor="#EDEAE2", showocean=True, oceancolor="#EAF4FB",
                            showcountries=True, countrycolor="#FFFFFF", showframe=False, showcoastlines=False)
        map_fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), coloraxis_showscale=False)
        st.plotly_chart(map_fig, use_container_width=True)

# ----------------------------------------------------------------------
# 2. Conversion: participation -> results (analysis + E9)
# ----------------------------------------------------------------------
section("2", "Conversion — does participation turn into results?", "E9 · analysis")
avg_rate = total_top10 / total_riders
nat_plot = nat.assign(label=nat.apply(
    lambda r: r["rider_country_code"] if (r["riders"] >= 5 or r["stage_top10"] >= 10) else "", axis=1))
fig_c = px.scatter(
    nat_plot, x="riders", y="stage_top10", size="stage_podiums", size_max=30, text="label",
    color="top10_per_rider", color_continuous_scale="RdYlGn", hover_name="rider_country",
    custom_data=["best_gc", "stage_wins", "stage_podiums", "top10_per_rider"],
    labels={"riders": "Riders in the race", "stage_top10": "Stage top-10 finishes", "top10_per_rider": "Top-10s per rider"},
    title="Riders vs stage top-10s (bubble = stage podiums; above the dashed line = converts better than average)",
)
fig_c.add_trace(go.Scatter(x=[0, nat["riders"].max()], y=[0, nat["riders"].max() * avg_rate], mode="lines",
                           line=dict(dash="dash", color="#888"), name=f"Average: {avg_rate:.2f} top-10s / rider",
                           hoverinfo="skip"))
fig_c.update_traces(selector=dict(mode="markers+text"), textposition="top center",
                    hovertemplate="<b>%{hovertext}</b><br>Riders %{x} · top-10s %{y}<br>Best GC #%{customdata[0]} · "
                    "stage wins %{customdata[1]} · podiums %{customdata[2]}<br>%{customdata[3]:.2f} top-10s per rider<extra></extra>")
fig_c.update_layout(height=480, coloraxis_showscale=False, legend=dict(orientation="h", y=-0.15))
st.plotly_chart(style_fig(fig_c), use_container_width=True)

host_top10_share = host["stage_top10"] / total_top10
insight_card(
    f"<b>{host['rider_country']}</b> supplies {host['riders'] / total_riders:.0%} of riders but only "
    f"{host_top10_share:.0%} of stage top-10s, with a best GC of #{int(host['best_gc'])} — presence without conversion. "
    f"<b>{eff['rider_country']}</b> turned {int(eff['riders'])} riders into {int(eff['stage_top10'])} top-10s "
    f"({eff['top10_per_rider']:.1f} per rider, {eff['top10_per_rider'] / avg_rate:.1f}× the average) "
    f"and {int(eff['stage_wins'])} stage win(s)."
)

tbl = nat.copy()
tbl["Best GC"] = tbl["best_gc"].map(lambda v: f"#{int(v)}" if v == v else "—")
st.dataframe(
    tbl[["rider_country", "teams", "riders", "finishers", "Best GC", "gc_top10", "stage_wins", "stage_podiums",
         "stage_top10", "top10_per_rider"]].rename(columns={
        "rider_country": "Nation", "teams": "Teams", "riders": "Riders", "finishers": "Finishers",
        "gc_top10": "GC top-10 riders", "stage_wins": "Stage wins", "stage_podiums": "Stage podiums",
        "stage_top10": "Stage top-10s"}),
    hide_index=True, use_container_width=True, height=380,
    column_config={"top10_per_rider": st.column_config.ProgressColumn(
        "Top-10s per rider", min_value=0.0, max_value=float(nat["top10_per_rider"].max()), format="%.2f")},
)

# ----------------------------------------------------------------------
# 3. Drill into a nation (E8 / E9 pathway back to athletes and stages)
# ----------------------------------------------------------------------
section("3", "Open a nation — its riders, teams and best days", "E8 · E9")
country = st.selectbox("Nation", nat["rider_country"].tolist(), index=0)
code = nat.loc[nat["rider_country"] == country, "rider_country_code"].iloc[0]
cr = riders[riders["rider_country_code"] == code].copy()
cr["Foreign team?"] = cr["team_country_code"] != code
cr["GC"] = cr.apply(lambda r: f"#{int(r['gc_rank'])}" if r["gc_rank"] == r["gc_rank"] else f"Exit S{int(r['exit_stage'])}", axis=1)

d1, d2 = st.columns([1.2, 1], gap="medium")
with d1:
    st.markdown(f"**{len(cr)} {country} rider(s) across {cr['team'].nunique()} team(s)**")
    st.dataframe(cr.sort_values("gc_rank")[["rider_name", "team", "team_country", "Foreign team?", "age_at_start", "GC"]]
                 .rename(columns={"rider_name": "Rider", "team": "Team", "team_country": "Team country", "age_at_start": "Age"}),
                 hide_index=True, use_container_width=True, height=330)
with d2:
    best_days = res[(res["rider_country_code"] == code) & (res["rank"] <= 3)].sort_values(["rank", "stage_id"])
    st.markdown(f"**Stage podiums ({len(best_days)})**")
    if len(best_days):
        st.dataframe(best_days[["stage_id", "type_label", "rider_name", "rank", "gap_to_winner"]]
                     .assign(gap_to_winner=lambda d: d["gap_to_winner"].map(fmt_gap))
                     .rename(columns={"stage_id": "Stage", "type_label": "Type", "rider_name": "Rider", "rank": "Rank",
                                      "gap_to_winner": "Gap"}), hide_index=True, use_container_width=True, height=330)
    else:
        st.info("No stage podiums for this nation.")

home_teams = cr[~cr["Foreign team?"]]["team"].nunique()
insight_card(
    f"{(cr['Foreign team?']).mean():.0%} of {country}'s riders race for a team registered in another country"
    + (f"; {home_teams} home-registered team(s) employ the rest." if home_teams else ".")
)

so_what([
    f"<b>Federations:</b> {host['rider_country']}'s volume is not converting into GC results — investment should shift "
    "from quantity of pros to developing a few riders capable of top-10 stage results on mountain and ITT days.",
    f"<b>Sponsors & broadcasters:</b> {eff['rider_country']} and other high-conversion nations deliver outsized "
    "on-screen presence per rider — strong markets for rider-level sponsorship and audience campaigns.",
    f"<b>Teams:</b> {cross_share:.0%} of riders race for foreign-registered teams — scouting should be global; "
    "nationality of the team is not a constraint on talent.",
])
