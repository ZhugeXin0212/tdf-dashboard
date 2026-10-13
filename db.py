"""
Database connection module for the Tour de France dashboard.

Connects to the Supabase Postgres instance populated by
`Relational Schema/load_to_postgres.py`. The connection string is never
hardcoded here -- it is read from (in order of preference):

1. Streamlit secrets (`.streamlit/secrets.toml`, key "DATABASE_URL")
   -- used both locally and on Streamlit Community Cloud.
2. The DATABASE_URL environment variable -- useful for quick local
   testing without creating a secrets file.

See `.streamlit/secrets.toml.example` for the expected format.
"""

import os

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def _get_db_url() -> str | None:
    try:
        if "DATABASE_URL" in st.secrets:
            return st.secrets["DATABASE_URL"]
    except Exception:
        # st.secrets raises if no secrets.toml exists at all -- that's
        # fine, we just fall back to the environment variable below.
        pass
    return os.environ.get("DATABASE_URL")


@st.cache_resource(show_spinner=False)
def get_engine() -> Engine:
    """Create (and cache for the app's lifetime) a single SQLAlchemy engine."""
    db_url = _get_db_url()
    if not db_url:
        st.error(
            "DATABASE_URL is not configured.\n\n"
            "- Locally: create `.streamlit/secrets.toml` from the "
            "`.streamlit/secrets.toml.example` template, or set the "
            "DATABASE_URL environment variable.\n"
            "- On Streamlit Community Cloud: add DATABASE_URL under "
            "'App settings -> Secrets'."
        )
        st.stop()
    return create_engine(db_url, pool_pre_ping=True)


@st.cache_data(ttl=600, show_spinner=False)
def run_query(sql: str, params: dict | None = None) -> pd.DataFrame:
    """Run a read-only SQL query against Postgres and return a DataFrame.

    Results are cached for 10 minutes. The underlying race data is
    static (the 2023 Tour de France is long over), so a short cache is
    safe and keeps the dashboard responsive when users change filters
    that map to the same underlying query.
    """
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(sql, conn, params=params)
