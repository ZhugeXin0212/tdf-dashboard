"""
Reference -- Requirement map & method.

Maps every project requirement (Task 3a-e) and every suggested OLAP
demonstration prompt (E1-E15) to the page and section that answers it,
and documents metric definitions and data limitations. Useful as the
script for the live demo and for the Task 4 report.
"""

import pandas as pd
import streamlit as st

from style import page_header, section

page_header("🧭 Requirement Map & Method", "Where each requirement is answered, how the metrics are defined, and data caveats.")

section("A", "Storyline of the dashboard")
st.markdown(
    """
| Step | Page | Question answered |
|---|---|---|
| 0 | **Executive Summary** | What decided this Tour, in six headline findings? |
| 1 | **Race Storyline** | How did the GC unfold, and on which terrain was the margin built? |
| 1 | **Stage Analysis** | Which stages separated the favourites and cost teams riders? Any stage in focus. |
| 2 | **Riders & Classifications** | Do the classifications reward the same riders? Who is consistently at the front? |
| 2 | **Terrain & Rider Profiles** | Which rider profile wins? Who gains when the terrain changes? |
| 3 | **Team Strategy** | Depth or stars? Who carried the team's time? How exposed was each team's plan? |
| 3 | **Nations** | Who supplies the peloton, and who converts participation into results? |
| ref | Rider / Team Directory | Look-ups and each rider's daily trace. |

Every analysis page follows the same pattern: **business question → headline findings → evidence (interactive,
drillable charts) → "So what?" implications** for a named stakeholder. All findings are computed live from the
database, so the narrative updates automatically if the data is reloaded.
"""
)

section("B", "Project Task 3 requirements")
st.dataframe(pd.DataFrame([
    ["3a Drill-down (stage → rider → team)", "Stage Analysis §4; Race Storyline §4; Team Strategy §2; Rider Profile"],
    ["3b Classification comparison (GC, Points, KOM, Young)", "Riders & Classifications §1–3"],
    ["3c Aggregate performance (cumulative time by rider, team, classification)", "Race Storyline §1–3; Team Strategy §2"],
    ["3d Country participation (teams & riders per country)", "Nations §1–3"],
    ["3e Design & presentation", "Storyline navigation, consistent colour coding of terrain, question/finding/so-what pattern"],
], columns=["Requirement", "Where"]), hide_index=True, use_container_width=True)

section("C", "Suggested OLAP demonstration prompts E1–E15")
st.dataframe(pd.DataFrame([
    ["E1", "GC leaderboard with contextual descent to the pivotal stage", "Race Storyline §4"],
    ["E2", "A stage in focus + team perspective of the top ten", "Stage Analysis §4"],
    ["E3", "Team burden & contribution (roll-up → riders → per-stage profiles)", "Team Strategy §2"],
    ["E4", "Parallel classifications (GC vs Young with age filter; Mountain GC proxy)", "Riders & Classifications §1, §3"],
    ["E5", "Mountain contours (podium frequency, mean gap; back to daily traces)", "Terrain & Rider Profiles §2"],
    ["E6", "Speed as a simple ratio by stage type, riders & teams", "Terrain & Rider Profiles §3"],
    ["E7", "Bonuses, penalties and counterfactual GC", "Race Storyline §5"],
    ["E8", "Participation by nation, opening to riders & teams", "Nations §1, §3"],
    ["E9", "National outcomes (best GC, wins/podiums) with pathway back", "Nations §2–3"],
    ["E10", "Temporal GC storyline with mountain stages & inflection points", "Race Storyline §1–2"],
    ["E11", "Against the clock: ITT catalogue", "Stage Analysis §3"],
    ["E12", "Consistency near the front (top-10 frequency + contributing stages)", "Riders & Classifications §4"],
    ["E13", "Depth of squads (distinct riders, rosters, countries)", "Team Strategy §4"],
    ["E14", "Top-ten intensity by team, by stage type, with drill-back", "Team Strategy §3"],
    ["E15", "The longest day + its leading finishers", "Stage Analysis §3"],
], columns=["Prompt", "Description", "Where"]), hide_index=True, use_container_width=True)

section("D", "Metric definitions")
st.markdown(
    """
- **Adjusted time** = finish time − time bonus + time penalty (per stage). **GC** = lowest cumulative adjusted time.
- **Best Team** = sum of the final adjusted times of each team's three fastest finishers (as stored in `award_team`).
- **Margin decomposition** = per-stage difference in adjusted time between two riders, summed by stage type;
  *seconds per 100 km* normalises by distance raced on that terrain.
- **Stage selectivity** = median time the final GC top-20 lost to the fastest of them on that stage.
- **Pace** = stage length ÷ adjusted time (km/h). **Pace index** = rider pace ÷ field average on that stage × 100.
- **% behind stage winner** = gap to winner ÷ winner's time; averaged over Mountain stages and over ITTs for the profile map.
- **Conversion** (nations) = stage top-10 finishes per rider. **ρ** = Spearman rank correlation.
- **Young Rider** = finishers whose age at the race start date is ≤ the selected cut-off (default 25).
"""
)

section("E", "Data limitations")
st.markdown(
    """
- No intermediate-sprint or categorised-climb data: **Points and King of the Mountains are proxies** derived from
  stage finish rank weighted by stage type (see Riders & Classifications).
- Exits record the stage *before which* the rider left; DNS and in-race withdrawals are both attributed to that stage.
- "Designated leader" comes from the `team.leader_bib` field; some leaders are sprinters whose goal was stage wins,
  so the *leader risk* view should be read together with each team's objective.
- One rider has no recorded nationality and is excluded from nation-level statistics.
"""
)
