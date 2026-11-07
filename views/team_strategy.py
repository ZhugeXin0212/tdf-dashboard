"""
3 · Stakeholder Views -- Team Strategy.

Suggested prompts E3 (team burden & contribution: roll up each team's
aggregate adjusted time, then open the aggregation to the riders and
their per-stage profiles), E13 (depth of squads) and E14 (top-ten
intensity by team, by stage type), framed as the questions a sports
director asks: depth or stars? who carried the load? how exposed were we
to losing our leader?
"""

import pandas as pd
import plotly.express as px
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

page_header("🏢 Team Strategy", "Depth vs star power, who carried each squad's time load, and leader risk.")
business_question(
    "What wins the team classification — a star or a deep squad — and how robust was each team's plan?",
    "Use: sports directors (selection & tactics), team owners and sponsors (where results come from).",
)

card = A.team_scorecard()
res = A.results()
riders = A.riders()
gcf = A.gc_final()
stg = A.stages()

rho_top10 = A.spearman(card["top10_finishes"], -card["best_team_rank"])
rho_wins = A.spearman(card["stage_wins"], -card["best_team_rank"])
rho_fin = A.spearman(card["finishers"], -card["best_team_rank"])
best = card.iloc[0]
most_wins = card.sort_values("stage_wins", ascending=False).iloc[0]
full = int((card["exits"] == 0).sum())

# ----------------------------------------------------------------------
# 1. Depth vs star power
# ----------------------------------------------------------------------
section("1", "Depth vs star power — what predicts the Best Team ranking?", "analysis")
k1, k2, k3, k4 = st.columns(4)
with k1:
    finding_card("Best Team", short_team(best["team"]),
                 f"{int(best['finishers'])}/{int(best['roster'])} finishers · {int(best['top10_finishes'])} stage top-10s · "
                 f"{int(best['stage_wins'])} wins", "#E6A817")
with k2:
    finding_card("Most stage wins", short_team(most_wins["team"]),
                 f"{int(most_wins['stage_wins'])} wins → Best Team #{int(most_wins['best_team_rank'])}", "#D32F2F")
with k3:
    finding_card("ρ(top-10 finishes, team rank)", f"{rho_top10:.2f}",
                 f"vs ρ = {rho_wins:.2f} for stage wins and {rho_fin:.2f} for finishers — depth at the front is what counts",
                 "#2E7D32")
with k4:
    finding_card("Squads that kept all riders", f"{full} / {len(card)}", "teams reaching Paris with a full roster", "#1565C0")

plot = card.copy()
# label only the teams worth talking about (top-5 Best Team + top-3 by
# stage wins); everything else is available on hover
notable = set(plot.nsmallest(5, "best_team_rank")["team"]) | set(plot.nlargest(3, "stage_wins")["team"])
plot["label"] = plot["team"].map(lambda t: short_team(t) if t in notable else "")
fig = px.scatter(
    plot, x="stage_wins", y="top10_finishes", size="finishers", size_max=28, color="best_team_rank",
    color_continuous_scale="YlOrRd_r", text="label",
    custom_data=["team", "best_team_rank", "finishers", "podiums", "best_gc"],
    labels={"stage_wins": "Stage wins (star power)", "top10_finishes": "Stage top-10 finishes (depth at the front)",
            "best_team_rank": "Best Team rank"},
    title="Teams by star power vs depth (bubble = finishers, colour = Best Team rank)",
)
fig.update_traces(textposition="middle right", textfont_size=10,
                  hovertemplate="<b>%{customdata[0]}</b><br>Best Team #%{customdata[1]}<br>Stage wins %{x} · "
                  "podiums %{customdata[3]} · top-10s %{y}<br>Finishers %{customdata[2]} · best GC #%{customdata[4]}<extra></extra>")
fig.update_layout(height=500, xaxis=dict(range=[-0.5, plot["stage_wins"].max() + 1.2], dtick=1))
st.plotly_chart(style_fig(fig), use_container_width=True)
insight_card(
    f"<b>{short_team(best['team'])}</b> won the team classification with only {int(best['stage_wins'])} stage win(s) but "
    f"{int(best['top10_finishes'])} top-10 finishes, while <b>{short_team(most_wins['team'])}</b> collected "
    f"{int(most_wins['stage_wins'])} wins and finished #{int(most_wins['best_team_rank'])}. The team prize counts the "
    "<i>three fastest riders</i>, so it rewards having several riders at the front, not one winner."
)

# ----------------------------------------------------------------------
# 2. Team burden and contribution (E3)
# ----------------------------------------------------------------------
section("2", "Team burden & contribution — open the aggregate to the riders", "E3")
roll = card[["team", "best_team_rank", "aggregate_time"]].sort_values("best_team_rank").copy()
roll["gap_min"] = (roll["aggregate_time"] - roll["aggregate_time"].min()) / 60
fig_r = px.bar(roll, x="gap_min", y="team", orientation="h", color="gap_min", color_continuous_scale="YlOrRd",
               labels={"gap_min": "Aggregate time behind Best Team (minutes)", "team": ""},
               title="Roll-up: team aggregate time (3 fastest finishers) — gap to the Best Team")
fig_r.update_traces(hovertemplate="<b>%{y}</b><br>Behind: %{x:.1f} min<extra></extra>")
fig_r.update_layout(height=560, coloraxis_showscale=False, yaxis=dict(autorange="reversed"))
st.plotly_chart(style_fig(fig_r), use_container_width=True)

team = st.selectbox("Open a team", card["team"].tolist(), index=0)
tr = riders[riders["team"] == team].copy()
fin = tr[tr["gc_time"].notna()].sort_values("gc_time")
counted = set(fin.head(3)["bib"])
agg_total = fin.head(3)["gc_time"].sum()
tr["Counted in team time"] = tr["bib"].isin(counted)
tr["Share of team time"] = tr.apply(lambda r: r["gc_time"] / agg_total if r["bib"] in counted else float("nan"), axis=1)
tr["Total time"] = tr["gc_time"].map(lambda v: seconds_to_hms(v) if pd.notna(v) else "—")
tr["Status"] = tr.apply(lambda r: f"GC #{int(r['gc_rank'])}" if pd.notna(r["gc_rank"])
                        else f"Exit S{int(r['exit_stage'])} ({r['exit_reason']})", axis=1)

bc1, bc2 = st.columns([1, 1.5], gap="medium")
with bc1:
    st.dataframe(
        tr.sort_values("gc_rank")[["rider_name", "Status", "Counted in team time", "Share of team time", "Total time"]]
        .rename(columns={"rider_name": "Rider", "Counted in team time": "Counted?", "Share of team time": "Share"}),
        hide_index=True, use_container_width=True,
        column_config={"Share": st.column_config.NumberColumn(format="percent", help="Share of the team's aggregate time"),
                       "Counted?": st.column_config.CheckboxColumn(help="One of the 3 fastest finishers counted for Best Team")},
    )
with bc2:
    tres = res[res["team"] == team]
    heat = tres.pivot_table(index="rider_name", columns="stage_id", values="gap_to_winner") / 60
    order = tr.sort_values("gc_rank")["rider_name"]
    heat = heat.reindex([n for n in order if n in heat.index])
    fig_h = px.imshow(heat, color_continuous_scale="RdYlGn_r", aspect="auto",
                      labels=dict(x="Stage", y="", color="Min behind winner"),
                      title="Per-stage profile: minutes behind the stage winner (blank = not started)")
    fig_h.update_layout(height=380, xaxis=dict(dtick=1, tickangle=0), margin=dict(l=10, r=10, t=60, b=30))
    st.plotly_chart(style_fig(fig_h), use_container_width=True)

# where did the team lose time vs the best team of each day?
day_team = (
    res.groupby(["stage_id", "team"])["adj_time"]
    .apply(lambda s: s.nsmallest(3).sum() if len(s) >= 3 else None)
    .dropna()
    .rename("team_day")
    .reset_index()
)
day_team["best_day"] = day_team.groupby("stage_id")["team_day"].transform("min")
mine = day_team[day_team["team"] == team].merge(stg[["stage_id", "type_label"]], on="stage_id")
mine["lost"] = mine["team_day"] - mine["best_day"]
lost_by_type = mine.groupby("type_label")["lost"].sum()
worst = mine.sort_values("lost", ascending=False).iloc[0]
counted_names = ", ".join(fin.head(3)["rider_name"])
insight_card(
    f"<b>{team}</b> — team time is carried by <b>{counted_names}</b>. Against the best team of each day it lost the most "
    f"on <b>{lost_by_type.idxmax()}</b> stages ({fmt_gap(lost_by_type.max())} in total); worst single day: "
    f"<b>Stage {int(worst['stage_id'])}</b> ({worst['type_label']}, {fmt_gap(worst['lost'])})."
)

# ----------------------------------------------------------------------
# 3. Top-ten intensity by team (E14)
# ----------------------------------------------------------------------
section("3", "Top-ten intensity by team — on which terrain does each squad perform?", "E14")
t10 = res[res["rank"] <= 10]
inten = t10.groupby(["team", "type_label"]).size().reset_index(name="top10")
order = card.sort_values("top10_finishes", ascending=False)["team"].tolist()
fig_i = px.bar(inten, x="top10", y="team", color="type_label", orientation="h", color_discrete_map=STAGE_TYPE_COLORS,
               category_orders={"team": order, "type_label": ["Flat", "Hilly", "Mountain", "ITT"]},
               labels={"top10": "Stage top-10 finishes", "team": "", "type_label": "Terrain"})
fig_i.update_layout(height=620, barmode="stack", legend=dict(orientation="h", y=1.0, yanchor="bottom", x=0),
                    margin=dict(t=50))
ic1, ic2 = st.columns([1.5, 1], gap="medium")
with ic1:
    st.plotly_chart(style_fig(fig_i), use_container_width=True)
with ic2:
    mix = inten.pivot_table(index="team", columns="type_label", values="top10", fill_value=0)
    mix = mix[mix.sum(axis=1) >= 5]  # ignore teams with very few top-10s
    mix_share = mix.div(mix.sum(axis=1), axis=0)
    flat_heavy = mix_share.get("Flat", pd.Series(dtype=float)).sort_values(ascending=False)
    mtn_heavy = mix_share.get("Mountain", pd.Series(dtype=float)).sort_values(ascending=False)
    insight_card(
        f"<b>{short_team(order[0])}</b> leads with {int(card.set_index('team').loc[order[0], 'top10_finishes'])} top-10s "
        f"spread across terrains. Among teams with 5+ top-10s, most flat-dependent: <b>{short_team(flat_heavy.index[0])}</b> "
        f"({flat_heavy.iloc[0]:.0%} on Flat stages); most mountain-dependent: <b>{short_team(mtn_heavy.index[0])}</b> "
        f"({mtn_heavy.iloc[0]:.0%})."
    )
    tpick = st.selectbox("Drill into a team's top-10 finishes", order)
    st.dataframe(t10[t10["team"] == tpick][["stage_id", "type_label", "rider_name", "rank"]].rename(
        columns={"stage_id": "Stage", "type_label": "Type", "rider_name": "Rider", "rank": "Rank"}),
        hide_index=True, use_container_width=True, height=330)

# ----------------------------------------------------------------------
# 4. Depth of squads & leader risk (E13)
# ----------------------------------------------------------------------
section("4", "Depth of squads & leader risk", "E13")
lead = riders[riders["is_leader"]].set_index("team")
best_gc_rider = gcf.sort_values("gc_rank").groupby("team").head(1).set_index("team")


def verdict(t: str) -> str:
    if t not in lead.index:
        return "No leader recorded"
    lr = lead.loc[t]
    if pd.isna(lr["gc_rank"]):
        return "⚠️ Leader abandoned"
    if t in best_gc_rider.index and best_gc_rider.loc[t, "bib"] != lr["bib"]:
        return "🔄 Plan B finished higher"
    return "✅ Leader delivered"


def leader_gc(t: str) -> str:
    if t not in lead.index:
        return "—"
    v = lead.loc[t, "gc_rank"]
    return f"#{int(v)}" if pd.notna(v) else "DNF"


depth = card[["team", "roster", "finishers", "exits", "nationalities", "best_team_rank"]].copy()
depth["Designated leader"] = depth["team"].map(lambda t: lead.loc[t, "rider_name"] if t in lead.index else "—")
depth["Leader GC"] = depth["team"].map(leader_gc)
depth["Best GC rider"] = depth["team"].map(
    lambda t: f"{best_gc_rider.loc[t, 'rider_name']} (#{int(best_gc_rider.loc[t, 'gc_rank'])})" if t in best_gc_rider.index else "—")
depth["Verdict"] = depth["team"].map(verdict)
vc = depth["Verdict"].value_counts()

dc1, dc2, dc3 = st.columns(3)
with dc1:
    finding_card("Leader delivered", f"{vc.get('✅ Leader delivered', 0)} teams",
                 "designated leader was the team's best GC finisher", "#2E7D32")
with dc2:
    finding_card("Plan B finished higher", f"{vc.get('🔄 Plan B finished higher', 0)} teams",
                 "a team-mate outperformed the designated leader on GC", "#6A1B9A")
with dc3:
    finding_card("Leader abandoned", f"{vc.get('⚠️ Leader abandoned', 0)} teams",
                 "the team's main objective ended before Paris", "#D32F2F")

st.dataframe(
    depth[["team", "Verdict", "Designated leader", "Leader GC", "Best GC rider", "finishers", "exits", "nationalities",
           "best_team_rank"]].rename(columns={"team": "Team", "finishers": "Finishers", "exits": "Exits",
                                              "nationalities": "Nationalities", "best_team_rank": "Best Team rank"}),
    hide_index=True, use_container_width=True, height=420,
    column_config={"Finishers": st.column_config.ProgressColumn(min_value=0, max_value=int(card["roster"].max()), format="%d"),
                   "Best Team rank": st.column_config.NumberColumn(width="small")},
)
exit_corr = A.spearman(card["exits"], card["best_team_rank"])
st.caption(f"Rank correlation between number of exits and Best Team rank: ρ = {exit_corr:.2f} "
           "(positive = teams that lost riders tended to rank lower). Note: some designated leaders are sprinters "
           "whose objective was stage wins, not GC.")
with st.expander("📋 Open a full roster (riders and countries)"):
    rt = st.selectbox("Team roster", card["team"].tolist(), key="roster_team")
    st.dataframe(riders[riders["team"] == rt][["bib", "rider_name", "rider_country", "age_at_start", "status", "gc_rank"]]
                 .rename(columns={"bib": "Bib", "rider_name": "Rider", "rider_country": "Nation", "age_at_start": "Age",
                                  "status": "Status", "gc_rank": "GC"}), hide_index=True, use_container_width=True)

so_what([
    "<b>Selection:</b> if the team classification (and the sponsor exposure that comes with it) is an objective, "
    "pick 3–4 riders able to finish near the front on Mountain days rather than one star plus pure helpers.",
    f"<b>Leader risk:</b> {vc.get('⚠️ Leader abandoned', 0)} squads lost their designated leader and in "
    f"{vc.get('🔄 Plan B finished higher', 0)} more a team-mate finished higher — name and protect a credible "
    "second GC rider instead of committing the whole roster to one name.",
    "<b>Tactics:</b> the per-stage team-loss view shows which terrain costs your squad the most time against the "
    "best team of the day — that is where training camps and reconnaissance should focus.",
])
