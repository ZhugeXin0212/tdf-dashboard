# Tour de France Dashboard (BT5110 Task 3)

A self-built, cloud-deployable OLAP dashboard for the 2023 Tour de
France dataset, built with Streamlit + Plotly on top of the Postgres
database created in `../Relational Schema/`.

## Pages

| Page | Covers |
|---|---|
| `app.py` (Home) | KPI overview, GC & Best Team podiums, rider/team nationality mix |
| `pages/1_Stage_DrillDown.py` | Task 3a -- drill down by stage, then by rider/team |
| `pages/2_Classification_Comparison.py` | Task 3b -- GC, Points (proxy), KOM (proxy), Young Rider |
| `pages/3_Aggregate_Performance.py` | Task 3c -- cumulative time trends by rider/team, gap-to-winner |
| `pages/4_Country_Participation.py` | Task 3d -- teams/riders per country, nationality drill-down |

**Note on Points / King of the Mountains:** the raw source data has no
intermediate-sprint or climb-category points, so these two
classifications are simplified proxies derived from stage finish rank
and stage type. This is clearly flagged in-app and should be stated
the same way in the written report (see docstring at the top of
`pages/2_Classification_Comparison.py`).

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
