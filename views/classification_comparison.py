"""
2 · Performance Drivers -- Riders & Classifications.

Task 3b (classification comparison) plus suggested prompts E4 (parallel
classifications: GC vs Young Rider with an age filter anchored at race
start, and a Mountain-only GC proxy) and E12 (consistency near the
front).

DATA LIMITATION: the source data has no intermediate-sprint or
categorised-climb points, so Points and King of the Mountains are
SIMPLIFIED PROXIES built from stage finish rank weighted by stage type.
GC and Young Rider use real adjusted race time.
"""

import pandas as pd
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
    seconds_to_hms,
    shade_gradient,
    so_what,
    style_fig,
)

page_header("🏆 Riders & Classifications", "General Classification · Points · King of the Mountains · Young Rider · consistency")
business_question(
    "Do the four classifications reward the same riders — and who delivered consistently at the front?",
    "Use: recruitment & contract decisions (what profile wins what), sponsor visibility (who is at the front most often).",
)
with st.expander("ℹ️ Method note — Points and KOM are proxies"):
    st.markdown(
        "The data records only stage finish rank/time/bonus/penalty — no intermediate sprints or categorised climbs. "
        "Points and King of the Mountains are therefore **proxies**: `max(21 − stage rank, 0)` weighted by stage type "
        "(Points: flat 1.0, hilly 0.7, mountain 0.3, ITT 0.2 · KOM: flat 0.1, hilly 0.6, mountain 1.0, ITT 0.3). "
        "GC and Young Rider use the actual cumulative adjusted time."
    )

res = A.results()
riders = A.riders()
gcf = A.gc_final()
race_start = A.stages()["day"].min()

# ----------------------------------------------------------------------
# Build the four classifications
# ----------------------------------------------------------------------
POINTS_W = {"flat": 1.0, "hilly": 0.7, "mountain": 0.3, "individual time-trial": 0.2}
KOM_W = {"flat": 0.1, "hilly": 0.6, "mountain": 1.0, "individual time-trial": 0.3}
px_df = res[["bib", "rank", "type"]].copy()
px_df["base"] = (21 - px_df["rank"]).clip(lower=0)
px_df["points"] = px_df["base"] * px_df["type"].map(POINTS_W)
px_df["kom"] = px_df["base"] * px_df["type"].map(KOM_W)
proxy = px_df.groupby("bib")[["points", "kom"]].sum().reset_index().merge(
    riders[["bib", "rider_name", "team", "age_at_start", "gc_rank"]], on="bib")
proxy["points_rank"] = proxy["points"].rank(ascending=False, method="min").astype(int)
proxy["kom_rank"] = proxy["kom"].rank(ascending=False, method="min").astype(int)

age_cut = st.sidebar.slider("Young Rider: max age at race start", 21, 30, 25,
                            help=f"Age is computed at the race start date ({race_start:%d %b %Y}).")
young = gcf[gcf["age_at_start"] <= age_cut].copy()
young["young_rank"] = young["gc_time"].rank(method="min").astype(int)

tbl = gcf[["bib", "rider_name", "team", "gc_rank", "gc_time", "age_at_start"]].merge(
    proxy[["bib", "points", "kom", "points_rank", "kom_rank"]], on="bib", how="left").merge(
    young[["bib", "young_rank"]], on="bib", how="left")

# ----------------------------------------------------------------------
# 1. Leaderboards
# ----------------------------------------------------------------------
section("1", "Four leaderboards", "Task 3b")
t_gc, t_pts, t_kom, t_yng = st.tabs(["🟡 General Classification", "🟢 Points (proxy)", "🔴 KOM (proxy)", "⚪ Young Rider"])
with t_gc:
    d = gcf.head(20).copy()
    d["Time"] = d["gc_time"].map(seconds_to_hms)
    d["Gap"] = (d["gc_time"] - d["gc_time"].min()).map(fmt_gap)
    st.dataframe(d[["gc_rank", "rider_name", "team", "rider_country", "Time", "Gap"]].rename(
        columns={"gc_rank": "Rank", "rider_name": "Rider", "team": "Team", "rider_country": "Nation"}),
        hide_index=True, use_container_width=True)
with t_pts:
    d = proxy.sort_values("points_rank").head(20)
    st.dataframe(d[["points_rank", "rider_name", "team", "points", "gc_rank"]].rename(
        columns={"points_rank": "Rank", "rider_name": "Rider", "team": "Team", "gc_rank": "GC rank"}),
        hide_index=True, use_container_width=True,
        column_config={"points": st.column_config.ProgressColumn("Score (proxy)", min_value=0.0,
                                                                 max_value=float(d["points"].max()), format="%.1f")})
with t_kom:
    d = proxy.sort_values("kom_rank").head(20)
    st.dataframe(d[["kom_rank", "rider_name", "team", "kom", "gc_rank"]].rename(
        columns={"kom_rank": "Rank", "rider_name": "Rider", "team": "Team", "gc_rank": "GC rank"}),
        hide_index=True, use_container_width=True,
        column_config={"kom": st.column_config.ProgressColumn("Score (proxy)", min_value=0.0,
                                                              max_value=float(d["kom"].max()), format="%.1f")})
with t_yng:
    d = young.sort_values("young_rank").head(20).copy()
    d["Time"] = d["gc_time"].map(seconds_to_hms)
    st.caption(f"Finishers aged ≤ {age_cut} on {race_start:%d %b %Y} (adjust in the sidebar). {len(young)} eligible.")
    st.dataframe(d[["young_rank", "rider_name", "team", "age_at_start", "Time", "gc_rank"]].rename(
        columns={"young_rank": "Rank", "rider_name": "Rider", "team": "Team", "age_at_start": "Age",
                 "gc_rank": "Overall GC"}), hide_index=True, use_container_width=True)

# ----------------------------------------------------------------------
# 2. Do the classifications reward the same riders?
# ----------------------------------------------------------------------
section("2", "Do the classifications reward the same riders?", "analysis")
top_sets = {
    "GC": set(tbl.nsmallest(10, "gc_rank")["bib"]),
    "Points": set(proxy.nsmallest(10, "points_rank")["bib"]),
    "KOM": set(proxy.nsmallest(10, "kom_rank")["bib"]),
    "Young": set(young.nsmallest(10, "young_rank")["bib"]),
}
names = list(top_sets)
overlap = pd.DataFrame([[len(top_sets[a] & top_sets[b]) for b in names] for a in names], index=names, columns=names)
membership = pd.Series({b: sum(b in s for s in top_sets.values()) for b in set().union(*top_sets.values())})
multi = membership[membership >= 3].index
multi_names = riders.set_index("bib").loc[multi, "rider_name"].tolist()

oc1, oc2 = st.columns([1, 1.3], gap="medium")
with oc1:
    fig_o = px.imshow(overlap, text_auto=True, color_continuous_scale="YlOrBr",
                      labels=dict(color="Shared riders"), title="Riders shared between top-10s")
    fig_o.update_layout(height=360, coloraxis_showscale=False)
    st.plotly_chart(style_fig(fig_o), use_container_width=True)
with oc2:
    finding_card("GC ∩ KOM top-10", f"{overlap.loc['GC', 'KOM']} / 10",
                 "climbing ability and overall success are the same asset — the GC contenders also dominate the mountains", "#D32F2F")
    st.write("")
    finding_card("GC ∩ Points top-10", f"{overlap.loc['GC', 'Points']} / 10",
                 "sprinters form a separate market: a team cannot target the green and yellow jerseys with the same riders", "#2E7D32")
    st.write("")
    if multi_names:
        insight_card(f"In the top 10 of 3+ classifications: <b>{', '.join(multi_names)}</b> — the all-round profile that wins Tours.")

# ----------------------------------------------------------------------
# 3. Parallel classifications for one rider (E4)
# ----------------------------------------------------------------------
section("3", "Parallel classifications — one rider across all lenses", "E4")
# default to the 2nd-best young rider: a GC contender whose ranks differ
# across lenses (more instructive than the winner, who is #1 everywhere)
_yr = young.sort_values("young_rank")
_default_name = _yr.iloc[1]["rider_name"] if len(_yr) > 1 else tbl["rider_name"].iloc[0]
default_idx = int(tbl["rider_name"].tolist().index(_default_name))
rider_name = st.selectbox("Rider (finishers)", tbl["rider_name"].tolist(), index=default_idx)
row = tbl[tbl["rider_name"] == rider_name].iloc[0]

ranks = {
    "GC": row["gc_rank"],
    "Points (proxy)": row["points_rank"],
    "KOM (proxy)": row["kom_rank"],
    "Young Rider": row["young_rank"],
}
mc = st.columns(4)
for col, (k, v) in zip(mc, ranks.items()):
    col.metric(k, int(v) if pd.notna(v) else ("Not eligible" if k == "Young Rider" else "N/A"))

compare_df = pd.DataFrame({"classification": list(ranks), "rank": list(ranks.values())}).dropna().reset_index(drop=True)
BASE_HUES = {"GC": "#E6A817", "Points (proxy)": "#2E7D32", "KOM (proxy)": "#D32F2F", "Young Rider": "#1565C0"}
BAR_WIDTH, N_SEG = 0.4, 30
max_rank = float(compare_df["rank"].max()) if len(compare_df) else 1.0
shadow = max_rank * 0.015
compare_df["y_pos"] = range(len(compare_df) - 1, -1, -1)
cfig = go.Figure()
for _, r in compare_df.iterrows():
    cat, value, y = r["classification"], float(r["rank"]), r["y_pos"]
    cfig.add_trace(go.Bar(y=[y - 0.18], x=[value], base=[shadow], orientation="h", width=BAR_WIDTH,
                          marker=dict(color="rgba(0,0,0,0.14)", line=dict(width=0)), showlegend=False, hoverinfo="skip"))
    seg = value / N_SEG
    for i, c in enumerate(shade_gradient(BASE_HUES[cat], N_SEG)):
        cfig.add_trace(go.Bar(y=[y], x=[seg], base=[i * seg], orientation="h", width=BAR_WIDTH,
                              marker=dict(color=c, line=dict(width=0)), showlegend=False, hoverinfo="skip"))
    cfig.add_trace(go.Bar(y=[y], x=[value], base=[0], orientation="h", width=BAR_WIDTH,
                          marker=dict(color="rgba(0,0,0,0)"), showlegend=False,
                          hovertemplate=f"<b>{cat}</b><br>Rank: {int(value)}<extra></extra>"))
cfig.update_layout(title=f"{rider_name}: rank by classification (shorter bar = better)", barmode="overlay", bargap=0.4,
                   yaxis=dict(tickmode="array", tickvals=compare_df["y_pos"].tolist(), ticktext=compare_df["classification"].tolist()),
                   xaxis=dict(title="Rank"), height=110 * max(len(compare_df), 1) + 110)
st.plotly_chart(style_fig(cfig), use_container_width=True)

# Mountain-only GC proxy vs overall GC
st.markdown("##### ⛰️ Mountain-only GC proxy vs overall GC")
st.caption("Cumulative adjusted time on Mountain stages only (finishers), re-ranked and compared with the real GC. "
           "Positive = the rider climbs better, relative to the field, than the overall result suggests. "
           "Divergences are shown for the overall GC top 50 (lower down, ranks are dominated by riders who sat up).")
mtn = res[res["type"] == "mountain"].groupby("bib")["adj_time"].sum().rename("mtn_time").reset_index()
mc_df = gcf.merge(mtn, on="bib")
mc_df["mtn_rank"] = mc_df["mtn_time"].rank(method="min").astype(int)
mc_df["divergence"] = mc_df["gc_rank"].astype(int) - mc_df["mtn_rank"]
top_climb = mc_df[mc_df["gc_rank"] <= 50].sort_values("divergence", ascending=False).iloc[0]
sel_row = mc_df[mc_df["rider_name"] == rider_name]
dc1, dc2 = st.columns([1.3, 1], gap="medium")
with dc1:
    top50 = mc_df[mc_df["gc_rank"] <= 50]
    div = pd.concat([top50.nlargest(8, "divergence"), top50.nsmallest(8, "divergence")])
    fig_d = px.bar(div, x="divergence", y="rider_name", orientation="h", color="divergence",
                   color_continuous_scale="RdYlGn", custom_data=["gc_rank", "mtn_rank"],
                   labels={"divergence": "Overall GC rank − Mountain rank", "rider_name": ""},
                   title="Biggest divergences between overall and Mountain-only ranking")
    fig_d.update_traces(hovertemplate="<b>%{y}</b><br>GC #%{customdata[0]} · Mountain #%{customdata[1]}<extra></extra>")
    fig_d.update_layout(height=460, coloraxis_showscale=False, yaxis=dict(autorange="reversed"))
    st.plotly_chart(style_fig(fig_d), use_container_width=True)
with dc2:
    st.dataframe(mc_df.nsmallest(10, "mtn_rank")[["mtn_rank", "rider_name", "gc_rank"]].rename(
        columns={"mtn_rank": "Mtn rank", "rider_name": "Rider", "gc_rank": "Overall GC"}),
        hide_index=True, use_container_width=True, height=300)
    msg = (f"<b>{top_climb['rider_name']}</b> is #{int(top_climb['gc_rank'])} overall but "
           f"#{int(top_climb['mtn_rank'])} on Mountain stages (largest gain within the GC top 50) — a climber whose GC was lost elsewhere (ITT/hilly days, or one bad day).")
    if len(sel_row):
        s = sel_row.iloc[0]
        msg += f" Selected rider <b>{rider_name}</b>: GC #{int(s['gc_rank'])} vs Mountain #{int(s['mtn_rank'])}."
    insight_card(msg)

# ----------------------------------------------------------------------
# 4. Consistency near the front (E12)
# ----------------------------------------------------------------------
section("4", "Consistency near the front — who is in the top 10 most often?", "E12")
t10 = res[res["rank"] <= 10]
reg = t10.groupby(["bib", "rider_name", "team"]).agg(
    top10=("rank", "count"), wins=("rank", lambda s: int((s == 1).sum())), avg_rank=("rank", "mean")).reset_index()
by_type = t10.pivot_table(index="bib", columns="type_label", values="rank", aggfunc="count").fillna(0)
reg = reg.merge(by_type, left_on="bib", right_index=True).sort_values(["top10", "wins"], ascending=False).head(15)
no_win = reg[reg["wins"] == 0].head(1)

rc1, rc2 = st.columns([1.3, 1], gap="medium")
with rc1:
    long = reg.melt(id_vars=["rider_name"], value_vars=[c for c in ["Flat", "Hilly", "Mountain", "ITT"] if c in reg],
                    var_name="Terrain", value_name="Top-10s")
    from style import STAGE_TYPE_COLORS
    fig_c = px.bar(long, x="Top-10s", y="rider_name", color="Terrain", orientation="h",
                   color_discrete_map=STAGE_TYPE_COLORS, category_orders={"rider_name": reg["rider_name"].tolist()},
                   labels={"rider_name": ""}, title="Stage top-10 finishes, split by terrain")
    fig_c.update_layout(height=500, barmode="stack", legend=dict(orientation="h", y=1.0, yanchor="bottom", x=0),
                        margin=dict(t=90))
    st.plotly_chart(style_fig(fig_c), use_container_width=True)
with rc2:
    pick = st.selectbox("Contributing stages for", reg["rider_name"].tolist())
    pb = int(reg.loc[reg["rider_name"] == pick, "bib"].iloc[0])
    st.dataframe(t10[t10["bib"] == pb][["stage_id", "type_label", "rank", "gap_to_winner"]]
        .assign(gap_to_winner=lambda d: d["gap_to_winner"].map(fmt_gap)).rename(
        columns={"stage_id": "Stage", "type_label": "Type", "rank": "Rank", "gap_to_winner": "Gap to winner"}),
        hide_index=True, use_container_width=True, height=330)
    if len(no_win):
        nw = no_win.iloc[0]
        insight_card(f"<b>{nw['rider_name']}</b> made the top 10 <b>{int(nw['top10'])}</b> times without a single stage "
                     "win — high, steady visibility that stage-win counts alone would undervalue.")

so_what([
    "<b>Recruitment:</b> GC and KOM top-10s overlap heavily — one elite climber serves two objectives; the Points "
    "jersey needs a separate sprint-oriented roster. Teams must choose, not hedge.",
    f"<b>Talent pipeline:</b> {overlap.loc['GC', 'Young']} of the Young Rider top 10 (age ≤ {age_cut}) are also in the "
    "overall GC top 10 — young riders are already race-deciding assets, so early long-term contracts are a competitive lever.",
    "<b>Sponsor value:</b> rank riders by top-10 frequency, not only wins — consistent riders deliver far more "
    "on-screen time at the front of the race.",
])
