"""
1 · Race Outcome -- Stage Analysis.

Task 3a (drill-down) plus suggested prompts E2 (a stage in focus, with
team perspective), E11 (ITT catalogue) and E15 (the longest day). Adds
two analyses that make the stage view decision-relevant: a GC
"selectivity" score per stage, and where/why riders left the race.
"""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import analytics as A
from style import (
    STAGE_TYPE_COLORS,
    business_question,
    finding_card,
    fmt_gap,
    insight_card,
    kpi_row,
    page_header,
    section,
    seconds_to_hms,
    short_team,
    so_what,
    style_fig,
)

page_header("🗺️ Stage Analysis", "Which stages shaped the race — and a drill-down into any single day.")
business_question(
    "Which stages actually separated the GC contenders, which ones cost teams riders, and what happened on a given day?",
    "Use: organisers evaluating route design; teams planning effort and risk stage by stage.",
)

stg = A.stages()
res = A.results()
riders = A.riders()
sel = A.stage_selectivity(20)

# ----------------------------------------------------------------------
# 1. Selectivity
# ----------------------------------------------------------------------
section("1", "Decisive stages — how much GC time did each stage create?", "analysis")
st.caption(
    "Selectivity = median time the final GC top-20 lost to the fastest of them on that stage. "
    "High = the stage split the favourites; ~0 = they finished together."
)
by_type = sel.groupby("type_label").agg(stages=("stage_id", "count"), avg_sel=("selectivity", "mean"),
                                        total=("selectivity", "sum")).reindex(["Flat", "Hilly", "Mountain", "ITT"])
share_mtn = by_type.loc["Mountain", "total"] / by_type["total"].sum()
top3 = sel.sort_values("selectivity", ascending=False).head(3)
corr_len = A.spearman(sel["length"], sel["selectivity"])

c1, c2, c3 = st.columns(3)
with c1:
    finding_card("Mountain stages", f"{share_mtn:.0%} of GC time",
                 f"created by {int(by_type.loc['Mountain', 'stages'])} of {len(stg)} stages "
                 f"(avg {fmt_gap(by_type.loc['Mountain', 'avg_sel'])} per stage)", "#D32F2F")
with c2:
    finding_card("Flat stages", f"avg {fmt_gap(by_type.loc['Flat', 'avg_sel'])}",
                 "per stage among the top-20 — they finish in the bunch; flat days are about stage wins, not GC", "#2E7D32")
with c3:
    finding_card("Distance is not difficulty", f"ρ = {corr_len:.2f}",
                 "rank correlation between stage length and selectivity — terrain, not kilometres, splits the race", "#1565C0")

fig = go.Figure()
for t in ["Flat", "Hilly", "Mountain", "ITT"]:
    sub = sel[sel["type_label"] == t]
    fig.add_bar(
        x=sub["stage_id"], y=sub["selectivity"] / 60, name=t, marker_color=STAGE_TYPE_COLORS[t],
        customdata=sub[["route", "length", "winner", "same_time_as_winner"]].values,
        hovertemplate="<b>Stage %{x}</b> · " + t + "<br>%{customdata[0]} (%{customdata[1]:.0f} km)"
        "<br>Winner: %{customdata[2]}<br>Riders on winner's time: %{customdata[3]}"
        "<br>Selectivity: %{y:.1f} min<extra></extra>",
    )
for _, r in top3.iterrows():
    fig.add_annotation(x=r.stage_id, y=r.selectivity / 60, text=f"#{list(top3.stage_id).index(r.stage_id) + 1}",
                       showarrow=False, yshift=12, font=dict(color="#B71C1C", size=13))
fig.update_layout(height=400, xaxis=dict(dtick=1, title="Stage"), yaxis_title="Median minutes lost by GC top-20",
                  legend=dict(orientation="h", y=1.1))
st.plotly_chart(style_fig(fig), use_container_width=True)
insight_card(
    "The three most selective stages were "
    + "; ".join(f"<b>Stage {int(r.stage_id)}</b> ({r.type_label}, {r.route})" for r in top3.itertuples())
    + ". All three come in the second half of the route — the order behind the leaders is shaped late, when accumulated fatigue meets the biggest climbs."
    if (top3["stage_id"] > len(stg) / 2).all()
    else "The three most selective stages were "
    + "; ".join(f"<b>Stage {int(r.stage_id)}</b> ({r.type_label}, {r.route})" for r in top3.itertuples()) + "."
)

# ----------------------------------------------------------------------
# 2. Attrition
# ----------------------------------------------------------------------
section("2", "Attrition — where did riders leave the race?", "analysis")
ex = riders[riders["exit_stage"].notna()].merge(stg[["stage_id", "type_label", "route"]],
                                                left_on="exit_stage", right_on="stage_id")
ex_by = ex.groupby(["stage_id", "exit_reason"]).size().reset_index(name="riders")
mtn_share = (ex["type_label"] == "Mountain").mean()
second_half = (ex["stage_id"] > len(stg) / 2).mean()

ac1, ac2 = st.columns([1.5, 1], gap="medium")
with ac1:
    fig_e = px.bar(ex_by, x="stage_id", y="riders", color="exit_reason",
                   color_discrete_map={"DNS": "#EF6C00", "withdrawal": "#6A1B9A"},
                   labels={"stage_id": "Stage at which the rider exited", "riders": "Riders", "exit_reason": "Reason"},
                   title="Exits by stage (DNS = did not start; withdrawal = abandoned)")
    for _, s in stg[stg["type_label"] == "Mountain"].iterrows():
        fig_e.add_vrect(x0=s.stage_id - 0.5, x1=s.stage_id + 0.5, fillcolor="#D32F2F", opacity=0.08,
                        layer="below", line_width=0)
    fig_e.update_layout(height=340, xaxis=dict(dtick=1, range=[0.5, len(stg) + 0.5]))
    st.plotly_chart(style_fig(fig_e), use_container_width=True)
with ac2:
    finding_card("Exits at mountain stages", f"{mtn_share:.0%}",
                 f"vs {(stg['type_label'] == 'Mountain').mean():.0%} of stages being mountains; "
                 f"{second_half:.0%} of exits came in the second half of the race.", "#EF6C00")
    with st.expander(f"All {len(ex)} exits"):
        st.dataframe(
            ex.sort_values("stage_id")[["stage_id", "type_label", "rider_name", "team", "exit_reason"]].rename(
                columns={"stage_id": "Stage", "type_label": "Type", "rider_name": "Rider", "team": "Team",
                         "exit_reason": "Reason"}),
            hide_index=True, use_container_width=True,
        )

# ----------------------------------------------------------------------
# 3. Catalogues: ITT (E11) and the longest day (E15)
# ----------------------------------------------------------------------
section("3", "Race catalogues — against the clock & the longest day", "E11 · E15")
cc1, cc2 = st.columns(2, gap="medium")
with cc1:
    with st.container(border=True):
        st.markdown("**⏱️ Individual time-trial stages**")
        itt = sel[sel["type_label"] == "ITT"][["stage_id", "day", "route", "length", "winner", "winner_team", "selectivity"]].copy()
        itt["day"] = itt["day"].dt.strftime("%d %b")
        itt["GC spread"] = itt["selectivity"].map(fmt_gap)
        st.dataframe(itt.drop(columns="selectivity").rename(columns={
            "stage_id": "Stage", "day": "Date", "route": "Route", "length": "Km", "winner": "Winner",
            "winner_team": "Team"}), hide_index=True, use_container_width=True)
        km_itt = itt["length"].sum()
        st.caption(f"Only {km_itt:.0f} km ({km_itt / stg['length'].sum():.1%} of the route) — yet see the Race Storyline "
                   "for how much of the winning margin these stages produced.")
with cc2:
    with st.container(border=True):
        longest = stg.loc[stg["length"].idxmax()]
        st.markdown(f"**📏 The longest day — Stage {int(longest.stage_id)}, {longest.length:.0f} km ({longest.type_label})**")
        st.caption(f"{longest['day']:%d %b} · {longest.route}")
        lt = res[res["stage_id"] == longest.stage_id].nsmallest(8, "rank")
        lt = lt.assign(Time=lt["adj_time"].map(seconds_to_hms), Gap=lt["gap_to_winner"].map(fmt_gap))
        st.dataframe(lt[["rank", "rider_name", "team", "Time", "Gap"]].rename(
            columns={"rank": "Rank", "rider_name": "Rider", "team": "Team"}), hide_index=True, use_container_width=True)
        if st.button("Open this stage below ↓", use_container_width=True):
            st.session_state["dd_stage"] = longest["label"]

# ----------------------------------------------------------------------
# 4. A stage in focus (E2 + Task 3a drill-down)
# ----------------------------------------------------------------------
section("4", "A stage in focus — drill down to riders and teams", "E2 · Task 3a")
if "dd_stage" not in st.session_state:
    st.session_state["dd_stage"] = sel.sort_values("selectivity", ascending=False)["label"].iloc[0]
f1, f2, f3 = st.columns([2.2, 1.4, 0.8])
with f1:
    label = st.selectbox("Stage (defaults to the most selective)", stg["label"], key="dd_stage")
with f2:
    team_f = st.multiselect("Team filter (optional)", sorted(res["team"].unique()))
with f3:
    top_n = st.slider("Top N", 5, 50, 15, 5)

srow = sel[sel["label"] == label].iloc[0]
day = res[res["stage_id"] == srow.stage_id].sort_values("rank")
second_gap = int(day.iloc[1]["gap_to_winner"]) if len(day) > 1 else 0
in_top20 = A.gc_final().head(20)["bib"]
kpi_row([
    ("Type · distance", f"{srow.type_label} · {srow.length:.0f} km", f"{srow['day']:%a %d %b}"),
    ("Route", srow.route, ""),
    ("Winner", srow.winner, short_team(srow.winner_team)),
    ("Winning margin", fmt_gap(second_gap), "over 2nd place"),
    ("Riders on winner's time", f"{int(srow.same_time_as_winner)}",
     "bunch finish" if srow.same_time_as_winner >= 20 else "selective finish"),
    ("GC top-20 spread", fmt_gap(srow.selectivity), "median loss among favourites"),
])

view = day if not team_f else day[day["team"].isin(team_f)]
view = view.head(top_n).copy()
view["Adjusted"] = view["adj_time"].map(seconds_to_hms)
view["Gap"] = view["gap_to_winner"].map(fmt_gap)
view["GC contender"] = view["bib"].isin(in_top20)
tab_r, tab_t = st.tabs(["👤 Rider view", "🏢 Team view"])
with tab_r:
    st.dataframe(
        view[["rank", "rider_name", "team", "rider_country", "Adjusted", "Gap", "bonus", "penalty", "GC contender"]].rename(
            columns={"rank": "Rank", "rider_name": "Rider", "team": "Team", "rider_country": "Nationality",
                     "bonus": "Bonus s", "penalty": "Penalty s"}),
        hide_index=True, use_container_width=True,
        column_config={"GC contender": st.column_config.CheckboxColumn("Final GC top-20?")},
    )
    st.caption(f"Route: {srow.route} · {srow['day']:%A %d %B}")
with tab_t:
    t10 = day[day["rank"] <= 10].groupby("team").agg(riders=("bib", "count"), best=("rank", "min"),
                                                      names=("rider_name", lambda s: ", ".join(s))).reset_index()
    t10 = t10.sort_values(["riders", "best"], ascending=[False, True])
    fig_t = px.bar(t10, x="riders", y="team", orientation="h", color="riders", color_continuous_scale="YlOrBr",
                   custom_data=["names", "best"], labels={"riders": "Riders in stage top 10", "team": ""},
                   title="Which squads populated the top ten?")
    fig_t.update_traces(hovertemplate="<b>%{y}</b><br>%{x} rider(s): %{customdata[0]}<br>Best: #%{customdata[1]}<extra></extra>")
    fig_t.update_layout(height=60 + 34 * len(t10), coloraxis_showscale=False, yaxis=dict(autorange="reversed"))
    st.plotly_chart(style_fig(fig_t), use_container_width=True)
    lead_team = t10.iloc[0]
    insight_card(f"<b>{lead_team.team}</b> placed <b>{int(lead_team.riders)}</b> rider(s) in the top 10 "
                 f"({lead_team.names}) — {len(t10)} different teams shared the top 10 on this stage.")

so_what([
    "<b>Route design:</b> GC separation is driven by terrain type, not by distance — long flat transfer stages add "
    "kilometres but no sporting selection; mountain and time-trial days are where the race is decided.",
    "<b>Team planning:</b> flat stages are low-risk for GC leaders (they finish in the bunch) — the right day to "
    "let sprinters' lead-out trains spend energy; mountain stages need the full squad around the leader.",
    "<b>Risk management:</b> exits cluster on mountain stages and late in the race — budget for fatigue and "
    "crash risk in week 3 when deciding how many climbers vs. sprinters to select.",
])
