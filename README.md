# Tour de France Dashboard (BT5110 Task 3)

A self-built, cloud-deployable OLAP dashboard for the 2023 Tour de
France dataset, built with Streamlit + Plotly on top of the Postgres
database created in `../Relational Schema/`.

## Structure (business-dashboard storyline)

Every analysis page follows the same pattern: **business question →
headline findings → evidence (interactive, drillable charts) → "So
what?" implications** for a named stakeholder. All findings are
computed live from Postgres (`analytics.py`), so the narrative updates
automatically when the data is reloaded.

| Section | Page (`views/`) | Answers | Covers |
|---|---|---|---|
| Executive Summary | `home.py` | Six headline findings + race at a glance | — |
| 1 · Race Outcome | `race_story.py` | Yellow-jersey timeline, GC storyline, margin decomposition by terrain, pivotal stage, bonus counterfactual | 3c · E1 E7 E10 |
| | `stage_drilldown.py` | Stage selectivity, attrition, ITT / longest-day catalogues, stage in focus | 3a · E2 E11 E15 |
| 2 · Performance Drivers | `classification_comparison.py` | Four leaderboards, classification overlap, parallel ranks, Mountain GC proxy, consistency | 3b · E4 E12 |
| | `terrain_pace.py` | Climber vs time-trialist profile map, mountain contours, pace index by terrain | E5 E6 |
| 3 · Stakeholder Views | `team_strategy.py` | Depth vs star power, team burden & contribution, top-10 intensity, leader risk | 3c · E3 E13 E14 |
| | `country_participation.py` | Participation, conversion (riders → results), nation drill-down | 3d · E8 E9 |
| Reference | `all_riders.py`, `all_teams.py` | Directories + rider stage-by-stage profile | — |
| | `requirements_map.py` | Requirement → page map, metric definitions, data caveats | — |

Shared code: `analytics.py` (cached SQL loaders + insight helpers),
`style.py` (theme and storytelling components: `business_question`,
`finding_card`, `kpi_row`, `insight_card`, `so_what`).

**Note on Points / King of the Mountains:** the raw source data has no
intermediate-sprint or climb-category points, so these two
classifications are simplified proxies derived from stage finish rank
and stage type. This is clearly flagged in-app and should be stated
the same way in the written report (see docstring at the top of
`views/classification_comparison.py`).

## Local setup

1. Install dependencies (ideally in a virtualenv):
   ```bash
   pip install -r requirements.txt
   ```

2. Configure the database connection. Copy the example secrets file and
   fill in your real Supabase connection string:
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   # then edit .streamlit/secrets.toml with your real password
   ```
   `.streamlit/secrets.toml` is gitignored -- never commit it.

3. Run the app:
   ```bash
   streamlit run app.py
   ```
   It opens at http://localhost:8501.

## Deploying to Streamlit Community Cloud

1. Push this `Dashboard/` folder (including `requirements.txt`, but
   **not** `.streamlit/secrets.toml`) to a GitHub repo.
2. Go to https://share.streamlit.io, sign in, click "New app", point it
   at the repo and `app.py`.
3. In the app's "Settings -> Secrets", paste the same key/value you put
   in your local `secrets.toml`:
   ```toml
   DATABASE_URL = "postgresql://postgres.xxxx:[email protected]:5432/postgres"
   ```
4. Deploy. Streamlit Cloud will install `requirements.txt` and run
   `app.py` automatically.

## Data refresh

If `../Relational Schema/table/*.csv` changes (e.g. the data is
corrected or extended), re-run:
```bash
cd "../Relational Schema"
python3 load_to_postgres.py
```
This drops and recreates all 10 tables from the current CSVs, so the
dashboard always reflects the latest verified data without any changes
needed here.
