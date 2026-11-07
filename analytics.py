"""
Shared analytical layer for every page.

Each loader runs ONE SQL query against the Postgres schema (joins and
window functions are pushed down to the database) and is cached, so all
pages work from the same consistent base facts. The insight helpers
below then derive the business findings (winning margin decomposition,
stage selectivity, team depth, nation conversion ...) that the pages
narrate. Nothing is hard-coded: if the data is reloaded, every number
and every sentence on the dashboard updates automatically.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from db import run_query
from style import STAGE_TYPE_LABEL

# ----------------------------------------------------------------------
# Base loaders (one query each)
# ----------------------------------------------------------------------


@st.cache_data(ttl=600, show_spinner=False)
def stages() -> pd.DataFrame:
    df = run_query(
        """
        select stage_id, day, type, length::float as length,
               start_location, finish_location
        from stage
        order by stage_id
        """
    )
    df["day"] = pd.to_datetime(df["day"])
    df["type_label"] = df["type"].map(STAGE_TYPE_LABEL)
    df["route"] = df["start_location"] + " → " + df["finish_location"]
    df["label"] = df.apply(
        lambda r: f"Stage {r.stage_id} · {r.day:%d %b} · {r.route} [{r.type_label}, {r.length:.0f} km]",
        axis=1,
    )
    return df


@st.cache_data(ttl=600, show_spinner=False)
def results() -> pd.DataFrame:
    """Rider x stage fact table enriched with every dimension needed.

    gap_to_winner is computed in SQL with a window function
    (adjusted time minus the fastest adjusted time of that stage).
    """
    df = run_query(
        """
        select
            s.stage_id, s.day, s.type, s.length::float as length,
            s.start_location, s.finish_location,
            res.rank, res.bib, r.rider_name, r.team,
            r.rider_country_code, c.country_name as rider_country,
            res.time, res.bonus, res.penalty,
            (res.time - res.bonus + res.penalty) as adj_time,
            (res.time - res.bonus + res.penalty)
              - min(res.time - res.bonus + res.penalty) over (partition by s.stage_id)
              as gap_to_winner
        from result res
        join stage s  on s.day = res.day
        join rider r  on r.bib = res.bib
        left join country c on c.country_code = r.rider_country_code
        order by s.stage_id, res.rank
        """
    )
    df["type_label"] = df["type"].map(STAGE_TYPE_LABEL)
    df["route"] = df["start_location"] + " → " + df["finish_location"]
    df["pace_kmh"] = df["length"] / (df["adj_time"] / 3600.0)
    return df


@st.cache_data(ttl=600, show_spinner=False)
def riders() -> pd.DataFrame:
    """Rider dimension + final status, GC rank, exit info, age at race start."""
    df = run_query(
        """
        select
            r.bib, r.rider_name, r.dob, r.team,
            r.rider_country_code, c.country_name as rider_country,
            t.team_country_code, tc.country_name as team_country,
            (t.leader_bib = r.bib) as is_leader,
            a.rank as gc_rank, a.adjusted_time as gc_time,
            e.stage_id as exit_stage, e.reason as exit_reason
        from rider r
        join team t on t.team = r.team
        left join country c  on c.country_code = r.rider_country_code
        left join country tc on tc.country_code = t.team_country_code
        left join award_ind a on a.bib = r.bib
        left join exit_record e on e.bib = r.bib
        order by r.bib
        """
    )
    df["dob"] = pd.to_datetime(df["dob"])
    race_start = stages()["day"].min()
    df["age_at_start"] = ((race_start - df["dob"]).dt.days / 365.25).round(1)
    df["status"] = df["gc_rank"].notna().map({True: "Finished", False: "Withdrawn"})
    df["is_leader"] = df["is_leader"].fillna(False).astype(bool)
    return df


@st.cache_data(ttl=600, show_spinner=False)
def gc_daily() -> pd.DataFrame:
    """GC standing after every stage, with gap to that day's leader."""
    df = run_query(
        """
        select
            s.stage_id, s.type, g.day, g.bib, r.rider_name, r.team,
            g.cumulative_time, g.gc_rank,
            g.cumulative_time - min(g.cumulative_time) over (partition by g.day) as gap_to_leader
        from gc_standing g
        join stage s on s.day = g.day
        join rider r on r.bib = g.bib
        order by s.stage_id, g.gc_rank
        """
    )
    df["type_label"] = df["type"].map(STAGE_TYPE_LABEL)
    return df


@st.cache_data(ttl=600, show_spinner=False)
def teams() -> pd.DataFrame:
    df = run_query(
        """
        select
            t.team, t.team_country_code, c.country_name as team_country,
            t.leader_bib, lr.rider_name as leader_name,
            at.rank as best_team_rank, at.aggregate_time
        from team t
        left join country c on c.country_code = t.team_country_code
        left join rider lr on lr.bib = t.leader_bib
        left join award_team at on at.team = t.team
        order by at.rank nulls last
        """
    )
    return df


# ----------------------------------------------------------------------
# Insight helpers
# ----------------------------------------------------------------------


def gc_final() -> pd.DataFrame:
    r = riders()
    return r[r["gc_rank"].notna()].sort_values("gc_rank").reset_index(drop=True)


def winner_and_runner_up() -> tuple[pd.Series, pd.Series]:
    g = gc_final()
    return g.iloc[0], g.iloc[1]


def time_lost_vs(bib_ref: int, bib_other: int) -> pd.DataFrame:
    """Per-stage seconds that `bib_other` lost to `bib_ref` (positive =
    other was slower), on stages both completed."""
    res = results()
    a = res[res["bib"] == bib_ref].set_index("stage_id")["adj_time"]
    b = res[res["bib"] == bib_other].set_index("stage_id")["adj_time"]
    st_ = stages().set_index("stage_id")
    out = pd.DataFrame({"lost": (b - a)}).dropna()
    out = out.join(st_[["type_label", "length", "route", "day"]])
    out["lost"] = out["lost"].astype(int)
    return out.reset_index()


def margin_by_terrain(lost: pd.DataFrame) -> pd.DataFrame:
    """Aggregate a time_lost_vs() frame by stage type: seconds, share of
    margin, km raced and seconds-per-km (time 'efficiency' of terrain)."""
    agg = (
        lost.groupby("type_label")
        .agg(seconds=("lost", "sum"), km=("length", "sum"), stages=("stage_id", "count"))
        .reindex(["Flat", "Hilly", "Mountain", "ITT"])
        .fillna(0)
    )
    total = agg["seconds"].sum()
    agg["share"] = agg["seconds"] / total if total else 0
    agg["sec_per_100km"] = agg["seconds"] / agg["km"].where(agg["km"] > 0) * 100
    return agg.reset_index()


def stage_selectivity(top_n: int = 20) -> pd.DataFrame:
    """How much GC time each stage created among the final top-N:
    median seconds lost by those riders to the fastest of them."""
    res = results()
    top = gc_final().head(top_n)["bib"]
    sub = res[res["bib"].isin(top)].copy()
    sub["lost_in_group"] = sub["adj_time"] - sub.groupby("stage_id")["adj_time"].transform("min")
    sel = sub.groupby("stage_id")["lost_in_group"].median().rename("selectivity").reset_index()
    winners = res[res["rank"] == 1][["stage_id", "rider_name", "team"]].rename(
        columns={"rider_name": "winner", "team": "winner_team"}
    )
    bunch = (
        res[res["gap_to_winner"] == 0].groupby("stage_id").size().rename("same_time_as_winner").reset_index()
    )
    return (
        stages()
        .merge(sel, on="stage_id")
        .merge(winners, on="stage_id", how="left")
        .merge(bunch, on="stage_id", how="left")
    )


def leader_by_stage() -> pd.DataFrame:
    g = gc_daily()
    return g[g["gc_rank"] == 1][["stage_id", "type_label", "bib", "rider_name", "team"]].reset_index(drop=True)


def team_scorecard() -> pd.DataFrame:
    """One row per team with depth, star-power and attrition metrics."""
    r = riders()
    res = results()
    t = teams().set_index("team")
    sc = r.groupby("team").agg(
        roster=("bib", "count"),
        finishers=("gc_rank", "count"),
        nationalities=("rider_country_code", "nunique"),
        best_gc=("gc_rank", "min"),
        gc_top10=("gc_rank", lambda s: int((s <= 10).sum())),
    )
    sc["exits"] = sc["roster"] - sc["finishers"]
    sc["stage_wins"] = res[res["rank"] == 1].groupby("team").size()
    sc["podiums"] = res[res["rank"] <= 3].groupby("team").size()
    sc["top10_finishes"] = res[res["rank"] <= 10].groupby("team").size()
    sc = sc.fillna(0)
    for c in ["stage_wins", "podiums", "top10_finishes"]:
        sc[c] = sc[c].astype(int)
    sc = sc.join(t[["team_country", "leader_bib", "leader_name", "best_team_rank", "aggregate_time"]])
    return sc.reset_index().sort_values("best_team_rank")


def spearman(x: pd.Series, y: pd.Series) -> float:
    """Spearman rank correlation without needing scipy."""
    return float(x.rank().corr(y.rank()))


def nation_scorecard() -> pd.DataFrame:
    r = riders()
    res = results()
    t = teams()
    nat = r[r["rider_country_code"].notna()].groupby(["rider_country_code", "rider_country"]).agg(
        riders=("bib", "count"),
        finishers=("gc_rank", "count"),
        best_gc=("gc_rank", "min"),
        gc_top10=("gc_rank", lambda s: int((s <= 10).sum())),
    )
    nat = nat.reset_index().set_index("rider_country_code")
    nat["teams"] = t.groupby("team_country_code").size()
    nat["stage_wins"] = res[res["rank"] == 1].groupby("rider_country_code").size()
    nat["stage_podiums"] = res[res["rank"] <= 3].groupby("rider_country_code").size()
    nat["stage_top10"] = res[res["rank"] <= 10].groupby("rider_country_code").size()
    for c in ["teams", "stage_wins", "stage_podiums", "stage_top10"]:
        nat[c] = nat[c].fillna(0).astype(int)
    nat["top10_per_rider"] = nat["stage_top10"] / nat["riders"]
    return nat.reset_index().sort_values("riders", ascending=False)
