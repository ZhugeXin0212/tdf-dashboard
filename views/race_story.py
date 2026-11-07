"""
1 · Race Outcome -- Race Storyline.

Covers suggested prompts E10 (temporal GC storyline), E1 (GC leaderboard
with contextual descent to the pivotal stage) and E7 (bonuses,
penalties and counterfactual GC), and adds the analysis that turns them
into an answer: a decomposition of the winning margin by terrain.
"""

import pandas as pd
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
    page_header,
    section,
    seconds_to_hms,
    short_team,
    so_what,
    style_fig,
)

page_header("📈 Race Storyline", "How the General Classification unfolded — and where the race was actually won.")
business_question(
    "Which stages and which terrain decided the overall result, and was the outcome ever really in doubt?",
    "Use: sports directors deciding where to invest effort; organisers judging whether the route created suspense.",
)

stg = A.stages()
g = A.gc_daily()
gcf = A.gc_final()
winner, runner = A.winner_and_runner_up()
leaders = A.leader_by_stage()

# ----------------------------------------------------------------------
# 1. Yellow-jersey timeline
# ----------------------------------------------------------------------
section("1", "Who held the yellow jersey?", "E10")
changes = int((leaders["bib"] != leaders["bib"].shift()).sum() - 1)
holders = leaders["rider_name"].nunique()
w_days = int((leaders["bib"] == winner["bib"]).sum())
# stage from which the eventual winner never lost the lead
last_other = leaders.index[leaders["bib"] != winner["bib"]].max()
for_good = int(leaders.loc[last_other + 1, "stage_id"]) if pd.notna(last_other) and last_other + 1 < len(leaders) else 1

c1, c2, c3, c4 = st.columns(4)
with c1:
    finding_card("Lead changes", f"{changes}", f"across {holders} different jersey holders", "#E6A817")
with c2:
    finding_card("Winner in yellow", f"{w_days} / {len(stg)} stages", f"{winner['rider_name']}", "#E6A817")
with c3:
    finding_card("Lead held for good from", f"Stage {for_good}", f"{stg.loc[stg.stage_id == for_good, 'route'].iloc[0]}", "#D32F2F")
with c4:
    finding_card("Final margin", fmt_gap(runner["gc_time"] - winner["gc_time"]).lstrip("+"), f"over {runner['rider_name']}", "#1565C0")

ribbon = leaders.merge(stg[["stage_id", "route"]], on="stage_id")
fig_r = px.bar(
    ribbon, x="stage_id", y=[1] * len(ribbon), color="rider_name", text="rider_name",
    labels={"stage_id": "Stage", "rider_name": "Yellow jersey"},
)
fig_r.update_traces(
    textposition="inside", insidetextanchor="middle", textangle=-90,
    customdata=ribbon[["type_label", "route"]].values,
    hovertemplate="<b>Stage %{x}</b> (%{customdata[0]})<br>%{customdata[1]}<br>Leader: %{fullData.name}<extra></extra>",
)
fig_r.update_layout(height=200, yaxis=dict(visible=False), bargap=0.05, xaxis=dict(dtick=1),
                    margin=dict(t=10, b=10), legend=dict(orientation="h", y=-0.35))
st.plotly_chart(style_fig(fig_r), use_container_width=True)

# ----------------------------------------------------------------------
# 2. GC storyline (gap to the day's leader)
# ----------------------------------------------------------------------
section("2", "The GC storyline — gap to the race leader after each stage", "E10")
f1, f2 = st.columns([1, 2])
with f1:
    team_filter = st.multiselect("Filter riders by team (optional)", sorted(g["team"].unique()))
with f2:
    pool = gcf if not team_filter else gcf[gcf["team"].isin(team_filter)]
    default = pool.head(5)["rider_name"].tolist()
    picked = st.multiselect("Riders", pool["rider_name"].tolist(), default=default)

if picked:
    gd = g[g["rider_name"].isin(picked)].copy()
    gd["gap_min"] = gd["gap_to_leader"] / 60
    fig = px.line(
        gd, x="stage_id", y="gap_min", color="rider_name", markers=True,
        labels={"stage_id": "Stage", "gap_min": "Minutes behind leader", "rider_name": "Rider"},
    )
    for _, s in stg[stg["type_label"].isin(["Mountain", "ITT"])].iterrows():
        fig.add_vrect(x0=s.stage_id - 0.5, x1=s.stage_id + 0.5, layer="below", line_width=0,
                      fillcolor=STAGE_TYPE_COLORS[s.type_label], opacity=0.09)
    # inflection points: stages where the selected riders' gaps to the
    # leader moved the most (time swings), i.e. where standings reshuffled
    piv = gd.pivot_table(index="stage_id", columns="bib", values="gap_to_leader")
    swing = piv.diff().abs().sum(axis=1).sort_values(ascending=False)
    top_inf = [s for s in swing.head(3).index if swing[s] > 0]
    for sid in top_inf:
        fig.add_vline(x=sid, line_dash="dot", line_color="#555")
        fig.add_annotation(x=sid, y=1.02, yref="paper", text=f"↕ S{sid}", showarrow=False,
                           font=dict(size=11, color="#333"), bgcolor="#FFF1C2")
    fig.update_traces(customdata=gd[["gc_rank"]].values,
                      hovertemplate="<b>%{fullData.name}</b><br>Stage %{x}: +%{y:.1f} min · GC %{customdata[0]}<extra></extra>")
    fig.update_layout(height=470, xaxis=dict(dtick=1, range=[0.5, len(stg) + 0.5]))
    st.plotly_chart(style_fig(fig, hovermode="x unified"), use_container_width=True)
    st.caption("Red bands = Mountain, blue = ITT. ↕ = inflection stages: the largest combined time swings among the selected riders.")
    inf_types = stg.set_index("stage_id").loc[top_inf, "type_label"].tolist()
    insight_card(
        "The biggest time swings among the selected riders came on stages "
        + ", ".join(f"<b>{s}</b> ({t})" for s, t in zip(top_inf, inf_types))
        + (". None of them is a flat stage: the GC picture only changes where the road rises or the clock runs."
           if "Flat" not in inf_types else ".")
    )
else:
    st.info("Select at least one rider.")

# ----------------------------------------------------------------------
# 3. Where was the race won? (margin decomposition)
# ----------------------------------------------------------------------
section("3", "Where was the race won? — time lost to the winner, stage by stage", "analysis")
contenders = gcf[gcf["bib"] != winner["bib"]].head(20)
rival = st.selectbox(
    "Compare the winner with", contenders["rider_name"].tolist(), index=0,
    help="Defaults to the runner-up. Try any top-20 rider to see where they lost the Tour.",
)
rival_row = contenders[contenders["rider_name"] == rival].iloc[0]
lost = A.time_lost_vs(int(winner["bib"]), int(rival_row["bib"]))
terr = A.margin_by_terrain(lost)
total_lost = int(lost["lost"].sum())

lc, rc = st.columns([1.6, 1], gap="medium")
with lc:
    fig_m = go.Figure()
    for t in ["Flat", "Hilly", "Mountain", "ITT"]:
        sub = lost[lost["type_label"] == t]
        fig_m.add_bar(
            x=sub["stage_id"], y=sub["lost"], name=t, marker_color=STAGE_TYPE_COLORS[t],
            customdata=sub[["route", "length"]].values,
            hovertemplate="<b>Stage %{x}</b> · " + t + "<br>%{customdata[0]} (%{customdata[1]:.0f} km)"
            "<br>Time lost to winner: %{y}s<extra></extra>",
        )
    fig_m.update_layout(title=f"{rival} vs {winner['rider_name']}: seconds lost per stage (total {fmt_gap(total_lost)})",
                        xaxis=dict(dtick=1, title="Stage"), yaxis_title="Seconds lost (negative = gained)",
                        height=420, barmode="relative")
    st.plotly_chart(style_fig(fig_m), use_container_width=True)
with rc:
    show = terr.copy()
    show["Share"] = show["share"].map(lambda v: f"{v:.0%}")
    show["s / 100 km"] = show["sec_per_100km"].round(0)
    st.markdown("**Margin by terrain**")
    st.dataframe(
        show[["type_label", "km", "seconds", "Share", "s / 100 km"]].rename(
            columns={"type_label": "Terrain", "km": "Km", "seconds": "Seconds"}),
        hide_index=True, use_container_width=True,
        column_config={"Km": st.column_config.NumberColumn(format="%.0f")},
    )
    worst = lost.sort_values("lost", ascending=False).iloc[0]
    top_t = terr.sort_values("seconds", ascending=False).iloc[0]
    eff = terr.dropna(subset=["sec_per_100km"]).sort_values("sec_per_100km", ascending=False).iloc[0]
    insight_card(
        f"<b>{rival}</b> lost {fmt_gap(total_lost)} in total. <b>{top_t['share']:.0%}</b> came on "
        f"<b>{top_t['type_label']}</b> stages; the single costliest day was <b>Stage {int(worst['stage_id'])}</b> "
        f"({worst['type_label']}, {worst['lost']}s). Per kilometre, <b>{eff['type_label']}</b> was the most "
        f"expensive terrain ({eff['sec_per_100km']:.0f}s per 100 km)."
    )

# ----------------------------------------------------------------------
# 4. Contextual descent: a contender's pivotal stage (E1)
# ----------------------------------------------------------------------
section("4", "Follow a contender down to the stage grain — the pivotal moment", "E1")
who = st.selectbox("Contender (final GC top 20)", gcf.head(20)["rider_name"].tolist(), index=1, key="e1_rider")
bib = int(gcf.loc[gcf["rider_name"] == who, "bib"].iloc[0])
res = A.results()
trace = (
    res[res["bib"] == bib][["stage_id", "type_label", "route", "rank", "adj_time", "gap_to_winner", "bonus", "penalty"]]
    .merge(g[g["bib"] == bib][["stage_id", "gc_rank", "gap_to_leader"]], on="stage_id")
    .sort_values("stage_id")
)
trace["gc_move"] = -trace["gc_rank"].diff().fillna(0).astype(int)  # positive = climbed the GC
trace["gap_change"] = trace["gap_to_leader"].diff().fillna(trace["gap_to_leader"])
# pivotal = the stage that changed the rider's GC position most, measured
# in time vs the race leader (rank moves in week 1 are noisy because
# everyone is within seconds of each other)
pivot = trace.loc[trace["gap_change"].abs().idxmax()]
rank_move = trace.loc[trace["gc_move"].iloc[1:].abs().idxmax()] if len(trace) > 1 else trace.iloc[0]

p1, p2, p3 = st.columns(3)
with p1:
    finding_card("Final GC", f"#{int(gcf.loc[gcf.bib == bib, 'gc_rank'].iloc[0])}", f"{who}", "#E6A817")
with p2:
    finding_card("Pivotal stage (biggest time swing vs GC leader)", f"Stage {int(pivot['stage_id'])}",
                 f"{pivot['type_label']} · {fmt_gap(pivot['gap_change'])} vs the leader · GC #{int(pivot['gc_rank'])} after the stage",
                 "#D32F2F")
with p3:
    finding_card("Biggest GC rank move", f"Stage {int(rank_move['stage_id'])}",
                 f"{rank_move['type_label']} · {'+' if rank_move['gc_move'] > 0 else ''}{int(rank_move['gc_move'])} places → #{int(rank_move['gc_rank'])}",
                 "#1565C0")

fig_t = go.Figure()
fig_t.add_bar(x=trace["stage_id"], y=trace["gap_change"] / 60, name="Time lost (+) / gained (−) vs GC leader (min)",
              marker_color=[STAGE_TYPE_COLORS[t] for t in trace["type_label"]], opacity=0.75,
              customdata=trace[["type_label", "rank"]].values,
              hovertemplate="Stage %{x} (%{customdata[0]})<br>Stage rank %{customdata[1]}<br>vs GC leader: %{y:+.2f} min<extra></extra>")
fig_t.add_scatter(x=trace["stage_id"], y=trace["gc_rank"], name="GC rank after stage", yaxis="y2",
                  mode="lines+markers", line=dict(color="#1A1A1A", width=2),
                  hovertemplate="Stage %{x}: GC #%{y}<extra></extra>")
fig_t.add_annotation(x=pivot["stage_id"], y=pivot["gc_rank"], yref="y2", text="★ pivotal", showarrow=True,
                     arrowhead=2, ay=-35, font=dict(color="#B8860B", size=13))
fig_t.update_layout(
    height=400, xaxis=dict(dtick=1, title="Stage"),
    yaxis=dict(title="Minutes lost vs GC leader on the day"),
    yaxis2=dict(title="GC rank", overlaying="y", side="right", autorange="reversed", showgrid=False, tickformat="d"),
    legend=dict(orientation="h", y=1.12),
)
st.plotly_chart(style_fig(fig_t, hovermode="x unified"), use_container_width=True)
with st.expander(f"Stage-by-stage trace for {who}"):
    tbl = trace.copy()
    tbl["Adjusted time"] = tbl["adj_time"].map(seconds_to_hms)
    tbl["Gap to stage winner"] = tbl["gap_to_winner"].map(fmt_gap)
    tbl["Gap to GC leader"] = tbl["gap_to_leader"].map(fmt_gap)
    st.dataframe(
        tbl[["stage_id", "type_label", "route", "rank", "Adjusted time", "Gap to stage winner", "gc_rank", "gc_move", "Gap to GC leader"]]
        .rename(columns={"stage_id": "Stage", "type_label": "Type", "route": "Route", "rank": "Stage rank",
                         "gc_rank": "GC rank", "gc_move": "GC move"}),
        hide_index=True, use_container_width=True,
    )

# ----------------------------------------------------------------------
# 5. Bonuses, penalties and counterfactual GC (E7)
# ----------------------------------------------------------------------
section("5", "Did time bonuses or penalties change the outcome?", "E7")
bp = res.groupby("bib")[["bonus", "penalty"]].sum().reset_index()
cf = gcf.merge(bp, on="bib", how="left").fillna({"bonus": 0, "penalty": 0})

scen = st.radio("Replay the GC under:", ["Actual", "No bonuses", "No penalties", "No bonuses & no penalties"], horizontal=True)
cf["cf_time"] = cf["gc_time"]
if "bonuses" in scen:
    cf["cf_time"] = cf["cf_time"] + cf["bonus"]
if "penalties" in scen:
    cf["cf_time"] = cf["cf_time"] - cf["penalty"]
cf["cf_rank"] = cf["cf_time"].rank(method="min").astype(int)
cf["move"] = cf["gc_rank"].astype(int) - cf["cf_rank"]
top10_actual = set(cf.nsmallest(10, "gc_rank")["bib"])
top10_cf = set(cf.nsmallest(10, "cf_rank")["bib"])
entered = cf[cf["bib"].isin(top10_cf - top10_actual)]["rider_name"].tolist()
left_ = cf[cf["bib"].isin(top10_actual - top10_cf)]["rider_name"].tolist()
movers = int((cf.nsmallest(10, "cf_rank")["move"] != 0).sum())

bc1, bc2 = st.columns([1, 1.3], gap="medium")
with bc1:
    top_bonus = cf.sort_values("bonus", ascending=False).head(10)
    fig_b = go.Figure()
    fig_b.add_bar(y=top_bonus["rider_name"], x=top_bonus["bonus"], orientation="h", name="Bonus (s)", marker_color="#2E7D32")
    fig_b.add_bar(y=top_bonus["rider_name"], x=-top_bonus["penalty"], orientation="h", name="Penalty (s)", marker_color="#D32F2F")
    fig_b.update_layout(title="Largest cumulative bonuses (and penalties)", barmode="relative", height=380,
                        yaxis=dict(autorange="reversed"), xaxis_title="Seconds")
    st.plotly_chart(style_fig(fig_b), use_container_width=True)
with bc2:
    show = cf.nsmallest(10, "cf_rank").copy()
    show["Time"] = show["cf_time"].map(seconds_to_hms)
    show["Movement"] = show["move"].map(lambda v: "—" if v == 0 else (f"▲{v}" if v > 0 else f"▼{-v}"))
    st.dataframe(
        show.assign(team=show["team"].map(short_team))[["cf_rank", "rider_name", "team", "Time", "gc_rank", "Movement"]].rename(
            columns={"cf_rank": "Scenario rank", "rider_name": "Rider", "team": "Team", "gc_rank": "Actual GC"}),
        hide_index=True, use_container_width=True, height=388,
    )
w_b = cf.loc[cf.bib == winner["bib"], "bonus"].iloc[0]
r_b = cf.loc[cf.bib == runner["bib"], "bonus"].iloc[0]
net = int(w_b - r_b)
real_margin = int(runner["gc_time"] - winner["gc_time"])
insight_card(
    f"Bonuses were worth a net <b>{net}s</b> to {winner['rider_name']} over {runner['rider_name']} — only "
    f"<b>{net / real_margin:.0%}</b> of the {real_margin}s margin, so the podium order is robust. "
    f"Under <i>{scen}</i>, {movers} of the top-10 positions change"
    + (f"; entering the top 10: <b>{', '.join(entered)}</b>; dropping out: <b>{', '.join(left_)}</b>." if entered else
       " and the top-10 line-up stays the same.")
)

so_what([
    "<b>Teams:</b> GC is won on Mountain and ITT stages — concentrate leader protection, reconnaissance and "
    "equipment budget there; flat stages carry almost no GC risk, so conserve domestiques' energy on them.",
    "<b>Recruitment:</b> per kilometre the time-trial is the most decisive terrain — a GC leader who cannot "
    "time-trial gives away minutes that climbing must win back.",
    f"<b>Organisers:</b> the yellow jersey changed hands {changes} times but was held for good from Stage {for_good} — "
    f"the final {len(stg) - for_good} stages produced no lead change. Placing more selective terrain (or an ITT) "
    "in the last week would keep the GC open for longer and sustain audience interest.",
    "<b>Rules:</b> time bonuses reward aggression but did not decide this GC — they matter most in the first "
    "week, when the favourites are separated by seconds and the yellow jersey can change hands on a bonus.",
])
