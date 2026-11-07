"""
2 · Performance Drivers -- Terrain & Rider Profiles.

Suggested prompts E5 (mountain contours: podium frequency and mean gap
to the stage winner, with a way back to the daily traces) and E6 (speed
as a simple ratio length/time per stage type, for riders and teams,
showing who gains when terrain shifts toward Mountain). Adds a rider
profile map (climbing vs time-trial) that explains *why* the GC top 10
look the way they do.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

import analytics as A
from style import (
    STAGE_TYPE_COLORS,
    STAGE_TYPE_ORDER,
    business_question,
    finding_card,
    fmt_gap,
    insight_card,
    page_header,
    section,
    so_what,
    style_fig,
)

page_header("⛰️ Terrain & Rider Profiles", "Climbers, time-trialists and all-rounders — and how riders and teams pace each terrain.")
business_question(
    "Which rider profile wins the Tour, and which riders and teams gain when the terrain changes?",
    "Use: scouting & recruitment (profile gaps in a roster), stage-by-stage tactics.",
)

res = A.results()
gcf = A.gc_final()

# relative pace: rider's speed vs field average speed on the same stage (=100)
res = res.copy()
res["pace_index"] = res["pace_kmh"] / res.groupby("stage_id")["pace_kmh"].transform("mean") * 100
# % time behind the stage winner
res["pct_behind"] = res["gap_to_winner"] / (res["adj_time"] - res["gap_to_winner"]) * 100

# ----------------------------------------------------------------------
# 1. Rider profile map
# ----------------------------------------------------------------------
section("1", "Rider profile map — climbing vs time-trialling", "analysis")
prof = (
    res[res["type_label"].isin(["Mountain", "ITT"])]
    .pivot_table(index="bib", columns="type_label", values="pct_behind", aggfunc="mean")
    .dropna()
    .reset_index()
)
sprint = res[(res["type_label"].isin(["Flat", "Hilly"])) & (res["rank"] <= 10)].groupby("bib").size().rename("flat_hilly_top10")
prof = prof.merge(gcf[["bib", "rider_name", "team", "gc_rank"]], on="bib").merge(sprint, on="bib", how="left").fillna({"flat_hilly_top10": 0})
prof["GC group"] = pd.cut(prof["gc_rank"], [0, 10, 30, 1000], labels=["GC top 10", "GC 11–30", "GC 31+"])
mx, my = prof["Mountain"].median(), prof["ITT"].median()
prof["Profile"] = np.select(
    [(prof.Mountain <= mx) & (prof.ITT <= my), (prof.Mountain <= mx) & (prof.ITT > my), (prof.Mountain > mx) & (prof.ITT <= my)],
    ["All-rounder (GC type)", "Pure climber", "Time-trialist / rouleur"], "Sprinter / domestique",
)
top10_allround = int(((prof["gc_rank"] <= 10) & (prof["Profile"] == "All-rounder (GC type)")).sum())

pc1, pc2 = st.columns([2, 1], gap="medium")
with pc1:
    fig = px.scatter(
        prof, x="Mountain", y="ITT", color="GC group", size=prof["flat_hilly_top10"] + 3,
        color_discrete_map={"GC top 10": "#E6A817", "GC 11–30": "#1565C0", "GC 31+": "#B0BEC5"},
        hover_name="rider_name", custom_data=["team", "gc_rank", "flat_hilly_top10", "Profile"],
        labels={"Mountain": "Avg % behind stage winner — Mountain stages", "ITT": "Avg % behind stage winner — ITT"},
        title="Each dot = one finisher (bubble size = flat/hilly top-10s, i.e. sprint/punch ability)",
    )
    fig.update_traces(hovertemplate="<b>%{hovertext}</b> (%{customdata[0]})<br>GC #%{customdata[1]} · %{customdata[3]}"
                      "<br>Mountain: %{x:.1f}% · ITT: %{y:.1f}% behind<br>Flat/hilly top-10s: %{customdata[2]}<extra></extra>")
    fig.add_vline(x=mx, line_dash="dash", line_color="#999")
    fig.add_hline(y=my, line_dash="dash", line_color="#999")
    for x, y, txt, xa, ya in [(0.01, 0.02, "◣ ALL-ROUNDERS", "left", "bottom"), (0.99, 0.02, "TIME-TRIALISTS ◢", "right", "bottom"),
                              (0.01, 0.98, "◤ CLIMBERS", "left", "top"), (0.99, 0.98, "SPRINTERS / DOMESTIQUES ◥", "right", "top")]:
        fig.add_annotation(x=x, y=y, xref="paper", yref="paper", text=txt, showarrow=False, xanchor=xa, yanchor=ya,
                           font=dict(size=11, color="#888"))
    for i, (_, r) in enumerate(prof.nsmallest(3, "gc_rank").iterrows()):
        fig.add_annotation(x=r.Mountain, y=r.ITT, text=f"#{int(r.gc_rank)} {r.rider_name.split()[-1]}", showarrow=True,
                           arrowhead=0, ax=70, ay=-40 + i * 18, font=dict(size=10, color="#8a6700"), bgcolor="rgba(255,255,255,0.85)")
    fig.update_layout(height=520, legend=dict(orientation="h", y=1.08))
    st.plotly_chart(style_fig(fig), use_container_width=True)
with pc2:
    finding_card("GC top 10 in the all-rounder quadrant", f"{top10_allround} / 10",
                 "better than the median finisher both uphill and against the clock — a pure climber or pure "
                 "time-trialist does not win a Grand Tour", "#E6A817")
    st.write("")
    counts = prof["Profile"].value_counts().rename_axis("Profile").reset_index(name="Riders")
    st.dataframe(counts, hide_index=True, use_container_width=True)
    st.caption("Quadrants split at the median finisher. Small values = closer to the stage winner.")

# ----------------------------------------------------------------------
# 2. Mountain contours (E5)
# ----------------------------------------------------------------------
section("2", "Mountain contours — podium frequency and mean gap to the stage winner", "E5")
mres = res[res["type_label"] == "Mountain"]
n_mtn = mres["stage_id"].nunique()
ms = mres.groupby(["bib", "rider_name", "team"]).agg(
    podiums=("rank", lambda s: int((s <= 3).sum())), stages=("rank", "count"), avg_gap=("gap_to_winner", "mean")
).reset_index()
ms = ms[ms["stages"] >= max(3, n_mtn // 2)].sort_values(["podiums", "avg_gap"], ascending=[False, True])
best = ms.iloc[0]
min_gap = ms.sort_values("avg_gap").iloc[0]

mc1, mc2 = st.columns([1.4, 1], gap="medium")
with mc1:
    top = ms.head(15).copy()
    top["gap_label"] = top["avg_gap"].map(fmt_gap)
    fig_m = px.bar(top, x="podiums", y="rider_name", orientation="h", color="avg_gap", color_continuous_scale="RdYlGn_r",
                   text="gap_label", labels={"podiums": f"Mountain-stage podiums (of {n_mtn})", "rider_name": "",
                                             "avg_gap": "Mean gap (s)"},
                   title="Top climbers: podium frequency (bar) and mean gap to the stage winner (label & colour)")
    fig_m.update_traces(textposition="outside", cliponaxis=False,
                        hovertemplate="<b>%{y}</b><br>Podiums: %{x}<br>Mean gap: %{marker.color:.0f}s<extra></extra>")
    fig_m.update_layout(height=470, coloraxis_showscale=False, yaxis=dict(autorange="reversed"),
                        xaxis=dict(range=[0, top["podiums"].max() + 1.2], dtick=1))
    st.plotly_chart(style_fig(fig_m), use_container_width=True)
with mc2:
    same = best["bib"] == min_gap["bib"]
    insight_card(f"<b>{best['rider_name']}</b> podiumed on <b>{int(best['podiums'])}</b> of {n_mtn} Mountain stages"
                 + (f" and also has the smallest mean gap to the stage winner ({fmt_gap(min_gap['avg_gap'])}) — dominant on both signals."
                    if same else f"; the smallest mean gap belongs to <b>{min_gap['rider_name']}</b> ({fmt_gap(min_gap['avg_gap'])} per stage)."))
    who = st.selectbox("Return to the daily traces of", top["rider_name"].tolist())
    tr = mres[mres["rider_name"] == who][["stage_id", "route", "rank", "gap_to_winner"]].copy()
    tr["Gap"] = tr["gap_to_winner"].map(fmt_gap)
    st.dataframe(tr.drop(columns="gap_to_winner").rename(columns={"stage_id": "Stage", "route": "Route", "rank": "Rank"}),
                 hide_index=True, use_container_width=True)

# ----------------------------------------------------------------------
# 3. Pace profile (E6)
# ----------------------------------------------------------------------
section("3", "Speed as a simple ratio — who gains when the terrain shifts?", "E6")
st.caption("Pace = stage length ÷ adjusted time (km/h). Pace index = rider's pace ÷ field average on the same stage × 100 "
           "(100 = average; removes the fact that mountain stages are slower for everyone).")

team_idx = res.pivot_table(index="team", columns="type_label", values="pace_index", aggfunc="mean")[["Flat", "Hilly", "Mountain", "ITT"]]
team_idx["Mountain shift"] = team_idx["Mountain"] - team_idx[["Flat", "Hilly"]].mean(axis=1)
team_idx = team_idx.sort_values("Mountain", ascending=False)

tc1, tc2 = st.columns([1.5, 1], gap="medium")
with tc1:
    hm = px.imshow(team_idx[["Flat", "Hilly", "Mountain", "ITT"]].round(1), text_auto=".1f", aspect="auto",
                   color_continuous_scale="RdYlGn", color_continuous_midpoint=100,
                   labels=dict(color="Pace index", x="", y=""), title="Team pace index by terrain (100 = field average)")
    hm.update_layout(height=640, coloraxis_showscale=False)
    st.plotly_chart(style_fig(hm), use_container_width=True)
with tc2:
    gain = team_idx["Mountain shift"].sort_values()
    fig_g = px.bar(gain, orientation="h", color=gain.values, color_continuous_scale="RdYlGn",
                   labels={"value": "Mountain index − Flat/Hilly index", "team": ""},
                   title="Who gains when the road goes up?")
    fig_g.update_traces(hovertemplate="<b>%{y}</b><br>Shift: %{x:+.2f} pts<extra></extra>")
    fig_g.update_layout(height=640, showlegend=False, coloraxis_showscale=False)
    st.plotly_chart(style_fig(fig_g), use_container_width=True)
up, down = gain.index[-1], gain.index[0]
spread = (team_idx.max() - team_idx.min())
insight_card(f"Team pace indices differ by only <b>{spread['Flat']:.1f} pts</b> on Flat stages (everyone rides in the bunch) "
             f"but by <b>{spread['Mountain']:.1f} pts</b> on Mountain stages. <b>{up}</b> gains most when the road climbs "
             f"({gain.iloc[-1]:+.1f} pts vs its flat/hilly level), while <b>{down}</b> loses most ({gain.iloc[0]:+.1f} pts) — "
             "its strengths lie on flatter terrain.")

st.markdown("##### Compare individual riders or teams — raw pace (km/h)")
mode = st.radio("Compare by", ["Rider", "Team"], horizontal=True)
if mode == "Rider":
    opts = gcf["rider_name"].tolist()
    picked = st.multiselect("Riders", opts, default=opts[:3])
    dfp = res[res["rider_name"].isin(picked)].groupby(["rider_name", "type"])["pace_kmh"].mean().reset_index()
    color = "rider_name"
else:
    opts = A.teams()["team"].tolist()
    picked = st.multiselect("Teams", opts, default=opts[:3])
    dfp = res[res["team"].isin(picked)].groupby(["team", "type"])["pace_kmh"].mean().reset_index()
    color = "team"
if len(dfp):
    fig_p = px.bar(dfp, x="type", y="pace_kmh", color=color, barmode="group",
                   category_orders={"type": STAGE_TYPE_ORDER},
                   labels={"type": "Stage type", "pace_kmh": "Avg pace (km/h)", color: mode})
    fig_p.update_traces(hovertemplate="<b>%{fullData.name}</b><br>%{x}: %{y:.1f} km/h<extra></extra>")
    fig_p.update_layout(height=420)
    st.plotly_chart(style_fig(fig_p), use_container_width=True)

so_what([
    f"<b>Recruitment:</b> {top10_allround} of the GC top 10 are all-rounders — a GC project needs a leader who is "
    "above median both uphill and in the time-trial; specialists belong in support or stage-hunting roles.",
    "<b>Roster balance:</b> the team pace heatmap exposes each squad's terrain profile — sprint-built teams fade on "
    "Mountain days, so they should target flat-stage wins rather than the team classification.",
    "<b>Tactics:</b> mountain-stage podium frequency and small average gaps identify the riders rivals must mark on "
    "summit finishes — use the daily traces to study when they attack.",
])
