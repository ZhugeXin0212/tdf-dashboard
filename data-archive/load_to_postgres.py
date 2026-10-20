"""
Load the Tour de France dashboard data into a cloud Postgres instance
(e.g. Supabase). Run this once to (re)create the 10 final tables and
populate them from the CSV files in table/.

Usage:
    1. Set the DATABASE_URL environment variable to your Supabase
       connection string (Session Pooler recommended), e.g.:

       export DATABASE_URL="postgresql://postgres.xxxx:[email protected]:5432/postgres"

    2. Run:
       python3 load_to_postgres.py

The script is idempotent: it drops and recreates the 10 tables every
time it runs (see postgres_schema.sql), so re-running it is safe and
will not create duplicate rows.
"""

import os
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_FILE = BASE_DIR / "postgres_schema.sql"
TABLE_DIR = BASE_DIR / "table"

# Load order matters: a table must be loaded AFTER every table it
# references via a foreign key (country before team before rider, etc.)
#
# primary_key lists the column(s) that are NOT NULL / PRIMARY KEY in
# postgres_schema.sql for that table. Rows with a null value in any of
# these columns are dropped before insert: a primary key can never be
# NULL, and in this dataset a null here only ever represents a known
# "unknown" placeholder (e.g. the blank country row for a rider whose
# nationality is unrecorded). That case is already fully captured by
# rider.rider_country_code being NULL -- a NULL foreign key legitimately
# means "no reference", so no matching country row is required.
LOAD_ORDER = [
    ("country.csv", "country", ["country_code"]),
    ("team.csv", "team", ["team"]),
    ("rider.csv", "rider", ["bib"]),
    ("location.csv", "location", ["location"]),
    ("stage.csv", "stage", ["stage_id"]),
    ("result.csv", "result", ["day", "bib"]),
    ("exit.csv", "exit_record", []),
    ("award_ind.csv", "award_ind", []),
    ("award_team.csv", "award_team", []),
    ("gc_standing.csv", "gc_standing", ["day", "bib"]),
]

# Columns that are DATE in postgres_schema.sql. pandas reads CSV dates as
# plain strings by default, which to_sql then binds as VARCHAR -- Postgres
# refuses that implicit VARCHAR -> DATE cast inside a multi-row INSERT.
# Converting to real date objects up front makes to_sql bind them as DATE.
DATE_COLUMNS = {
    "rider": ["dob"],
    "stage": ["day"],
    "result": ["day"],
    "gc_standing": ["day"],
}


def get_engine():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable is not set.")
        print('Example: export DATABASE_URL="postgresql://postgres.xxxx:[email protected]:5432/postgres"')
        sys.exit(1)
    return create_engine(db_url)


def run_schema(engine):
    print("Creating tables from postgres_schema.sql ...")
    sql_text = SCHEMA_FILE.read_text()

    # Strip full-line "--" comments BEFORE splitting on ";". Otherwise a
    # semicolon that happens to appear inside a comment (e.g. explaining
    # "tool; using X") would be mistaken for a statement terminator.
    cleaned_lines = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        cleaned_lines.append(line)
    cleaned_sql = "\n".join(cleaned_lines)

    with engine.begin() as conn:
        for statement in cleaned_sql.split(";"):
            statement = statement.strip()
            if statement:
                conn.execute(text(statement))
    print("  schema created.")


def load_tables(engine):
    for csv_name, table_name, pk_cols in LOAD_ORDER:
        csv_path = TABLE_DIR / csv_name
        df = pd.read_csv(csv_path)
        # Normalise empty strings (e.g. the blank country_code/country_name
        # row produced after cleaning the 'NULL' literal) to real NaN so
        # they are inserted as SQL NULL rather than empty strings.
        df = df.replace({"": None})

        skipped = 0
        for col in pk_cols:
            before = len(df)
            df = df[df[col].notna()]
            skipped += before - len(df)
        if skipped:
            print(f"  note: skipped {skipped} row(s) from {csv_name} with a NULL primary key "
                  f"({pk_cols}) -- not a data loss, see comment in load_tables()")

        for col in DATE_COLUMNS.get(table_name, []):
            df[col] = pd.to_datetime(df[col]).dt.date

        df = df.where(df.notna(), None)
        df.to_sql(table_name, engine, if_exists="append", index=False, method="multi", chunksize=500)
        print(f"  loaded {len(df):>5} rows -> {table_name}")


def verify(engine):
    print("\nVerification (row counts in Postgres vs local CSV):")
    with engine.connect() as conn:
        for csv_name, table_name, pk_cols in LOAD_ORDER:
            csv_path = TABLE_DIR / csv_name
            df = pd.read_csv(csv_path)
            local_rows = len(df)
            expected_rows = local_rows
            for col in pk_cols:
                expected_rows -= df[col].isna().sum()
            db_rows = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
            status = "OK" if db_rows == expected_rows else "MISMATCH"
            note = "" if expected_rows == local_rows else f" (csv has {local_rows}, {local_rows - expected_rows} dropped as null-PK)"
            print(f"  {table_name:<15} expected={expected_rows:<6} postgres={db_rows:<6} [{status}]{note}")


def main():
    engine = get_engine()
    run_schema(engine)
    load_tables(engine)
    verify(engine)
    print("\nDone. Your Supabase Postgres database is ready.")


if __name__ == "__main__":
    main()
