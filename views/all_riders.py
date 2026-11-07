"""
Detail page: full roster of all registered riders.

Reached either via the sidebar navigation or by clicking a KPI card /
"View all" link on the Home page. Supports search and status filtering
so it works as a genuine drill-down target, not just a dump of rows.
"""

import plotly.graph_objects as go
import streamlit as st

import analytics as A
from db import run_query
from style import STAGE_TYPE_COLORS, fmt_gap, kpi_row, page_header, short_team, style_fig

page_header("🚴 Rider Directory & Profile", "Reference: every registered rider (search & filter), and any rider's stage-by-stage trace.")

riders_sql = """
    select
        r.bib,
        r.rider_name,
        r.dob,
        r.team,
        r.rider_country_code,
        c.country_name as rider_country_name,
        case when a.bib is not null then 'Finished' else 'Withdrawn / DNF' end as status,
        a.rank as gc_rank,
        a.adjusted_time,
        e.reason as exit_reason,
        e.stage_id as exit_stage
    from rider r
    left join country c on c.country_code = r.rider_country_code
    left join award_ind a on a.bib = r.bib
    left join exit_record e on e.bib = r.bib
    order by r.bib
"""
riders_df = run_query(riders_sql)

# Pre-fill the status filter if the user clicked a KPI card on Home
# that set this via session_state before switching pages.
default_status = st.session_state.pop("rider_status_filter", "All")

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    # Type-ahead dropdown: start typing to filter the option list live,
    # click a match to add it, click the "x" on a pill to clear it --
    # same interaction pattern as the rider selector on Classification
    # Comparison. Leaving it empty means "no name filter".
    rider_options = sorted(riders_df["rider_name"].unique().tolist())
    selected_riders = st.multiselect(
        "🔎 Search rider (type to filter, click to select)",
        rider_options,
        default=[],
        placeholder="Type a rider name…",
    )
with col2:
    status_filter = st.selectbox(
        "Status", ["All", "Finished", "Withdrawn"],
        index=["All", "Finished", "Withdrawn"].index(default_status) if default_status in ["All", "Finished", "Withdrawn"] else 0,
    )
with col3:
    teams = ["All teams"] + sorted(riders_df["team"].unique().tolist())
    team_filter = st.selectbox("Team", teams)

filtered = riders_df.copy()
if selected_riders:
    filtered = filtered[filtered["rider_name"].isin(selected_riders)]
if status_filter == "Finished":
    filtered = filtered[filtered["status"] == "Finished"]
elif status_filter == "Withdrawn":
    filtered = filtered[filtered["status"] == "Withdrawn / DNF"]
if team_filter != "All teams":
    filtered = filtered[filtered["team"] == team_filter]

st.caption(f"Showing **{len(filtered)}** of **{len(riders_df)}** riders.")

st.dataframe(
    filtered[
        ["bib", "rider_name", "dob", "team", "rider_country_name", "status", "gc_rank", "exit_reason", "exit_stage"]
    ].rename(
        columns={
            "bib": "Bib",
            "rider_name": "Rider",
            "dob": "Date of birth",
            "team": "Team",
            "rider_country_name": "Nationality",
            "status": "Status",
            "gc_rank": "GC rank",
            "exit_reason": "Exit reason",
            "exit_stage": "Exit stage",
        }
    ),
    hide_index=True,
    use_container_width=True,
    height=600,
)

st.divider()

# ----------------------------------------------------------------------
# Rider profile: return to the daily traces behind every summary
# ----------------------------------------------------------------------
st.subheader("👤 Rider profile — the daily trace behind every summary")
prof_name = st.selectbox(
    "Rider", sorted(riders_df["rider_name"].tolist()),
    index=sorted(riders_df["rider_name"].tolist()).index(A.gc_final().iloc[0]["rider_name"]),
)
pr = A.riders().set_index("rider_name").loc[prof_name]
tr = A.results()
tr = tr[tr["bib"] == pr["bib"]].merge(
    A.gc_daily()[["stage_id", "bib", "gc_rank", "gap_to_leader"]], on=["stage_id", "bib"], how="left")

kpi_row([
    ("Final GC", f"#{int(pr['gc_rank'])}" if pr["gc_rank"] == pr["gc_rank"] else f"Exit before S{int(pr['exit_stage'])}",
     pr["status"]),
    ("Team", short_team(pr["team"]), "designated leader" if pr["is_leader"] else ""),
    ("Nation · age", f"{pr['rider_country'] or '—'} · {pr['age_at_start']:.0f}", "age at race start"),
    ("Stage wins · top-10s", f"{int((tr['rank'] == 1).sum())} · {int((tr['rank'] <= 10).sum())}", f"{len(tr)} stages ridden"),
    ("Best stage result", f"#{int(tr['rank'].min())}" if len(tr) else "—", ""),
])

if len(tr):
    fig = go.Figure()
    fig.add_bar(x=tr["stage_id"], y=tr["rank"], name="Stage rank",
                marker_color=[STAGE_TYPE_COLORS[t] for t in tr["type_label"]],
                customdata=tr[["type_label", "route", "gap_to_winner"]].values,
                hovertemplate="Stage %{x} (%{customdata[0]})<br>%{customdata[1]}<br>Rank %{y} · "
                "%{customdata[2]}s behind winner<extra></extra>")
    fig.add_scatter(x=tr["stage_id"], y=tr["gc_rank"], name="GC rank after stage", mode="lines+markers",
                    line=dict(color="#1A1A1A"), hovertemplate="Stage %{x}: GC #%{y}<extra></extra>")
    fig.update_layout(height=380, yaxis=dict(autorange="reversed", title="Rank (1 = best)"),
                      xaxis=dict(dtick=1, title="Stage (bar colour = terrain)"), legend=dict(orientation="h", y=1.1),
                      title=f"{prof_name}: stage rank and GC rank, stage by stage")
    st.plotly_chart(style_fig(fig, hovermode="x unified"), use_container_width=True)
    with st.expander("Stage-by-stage table"):
        st.dataframe(tr[["stage_id", "type_label", "route", "rank", "gap_to_winner", "bonus", "penalty", "gc_rank", "gap_to_leader"]]
                     .assign(gap_to_winner=lambda d: d["gap_to_winner"].map(fmt_gap),
                             gap_to_leader=lambda d: d["gap_to_leader"].map(fmt_gap))
                     .rename(columns={"stage_id": "Stage", "type_label": "Type", "route": "Route", "rank": "Stage rank",
                                      "gap_to_winner": "Gap to winner", "bonus": "Bonus s", "penalty": "Penalty s",
                                      "gc_rank": "GC rank", "gap_to_leader": "Gap to GC leader"}),
                     hide_index=True, use_container_width=True)
