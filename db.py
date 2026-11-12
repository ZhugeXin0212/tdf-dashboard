"""
Database backend for the Tour de France dashboard.

Two interchangeable backends, selected automatically:

1. **DuckDB over bundled CSVs (default, zero-config, permanent).**
   The race data is static (the 2023 Tour de France is long over), so
   the app ships the full relational dataset as CSV files under
   `data-archive/table/`. DuckDB queries those CSVs directly with real
   SQL -- joins, window functions, everything the Postgres backend
   supports -- with no server, no credentials and no expiry. This is
   the backend used on Streamlit Community Cloud.

2. **Supabase Postgres (optional).** If a DATABASE_URL is provided
   (Streamlit secrets or environment variable), queries run against
   the original star-schema Postgres instance instead. Kept for
   parity with the BT5110 coursework setup.

Both paths expose the same `run_query(sql, params)` contract used by
`analytics.py` and the views, so switching backends requires no
changes anywhere else in the codebase.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

TABLE_DIR = Path(__file__).parent / "data-archive" / "table"


def _database_url() -> str | None:
    try:
        if "DATABASE_URL" in st.secrets:
            return st.secrets["DATABASE_URL"]
    except Exception:
        # st.secrets raises if no secrets.toml exists at all -- that's
        # fine, we just fall back to the environment variable below.
        pass
    return os.environ.get("DATABASE_URL")


@st.cache_resource(show_spinner=False)
def _get_duckdb():
    """One DuckDB connection for the app's lifetime; CSVs registered as views."""
    import duckdb

    con = duckdb.connect()  # in-memory: CSVs are read directly as tables
    for csv in sorted(TABLE_DIR.glob("*.csv")):
        # Table name = CSV stem; exit.csv -> exit_record (the Postgres
        # table name, because EXIT is a reserved word in SQL).
        name = "exit_record" if csv.stem == "exit" else csv.stem
        con.execute(
            "create view "
            + name
            + " as select * from read_csv(?, header = true)",
            [str(csv)],
        )
    return con


def _inline_params(sql: str, params: dict) -> str:
    """Substitute SQLAlchemy-style %(name)s placeholders with quoted literals.

    Safe in this app: every parameter is a UI-selected value from a
    fixed option list built from the same dataset (team / rider names),
    never free-form user input.
    """
    for key, value in params.items():
        safe = str(value).replace("'", "''")
        sql = sql.replace(f"%({key})s", "'" + safe + "'")
    return sql


@st.cache_resource(show_spinner=False)
def _get_postgres_engine():
    from sqlalchemy import create_engine

    db_url = _database_url()
    if not db_url:
        st.error(
            "No data backend available.\n\n"
            "The bundled CSV backend needs no configuration -- if you are "
            "seeing this, the `data-archive/table/` directory is missing. "
            "To use Postgres instead, add DATABASE_URL under Streamlit "
            "secrets or as an environment variable."
        )
        st.stop()
    return create_engine(db_url, pool_pre_ping=True)


@st.cache_data(ttl=600, show_spinner=False)
def run_query(sql: str, params: dict | None = None) -> pd.DataFrame:
    """Run a read-only SQL query and return a DataFrame.

    Routes to DuckDB-over-CSV by default, or to Postgres when a
    DATABASE_URL is configured. Results are cached for 10 minutes; the
    underlying race data is static, so a short cache is safe and keeps
    the dashboard responsive when users change filters that map to the
    same underlying query.
    """
    if _database_url():
        engine = _get_postgres_engine()
        with engine.connect() as conn:
            return pd.read_sql(sql, conn, params=params)

    con = _get_duckdb()
    if params:
        sql = _inline_params(sql, params)
    return con.execute(sql).df()
