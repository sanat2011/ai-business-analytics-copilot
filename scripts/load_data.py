#!/usr/bin/env python3
"""
Phase 1 — Create Snowflake objects and load RAW tables from local CSVs.

Prerequisites:
  1. python scripts/prepare_data.py
  2. Copy .env.example → .env and set Snowflake credentials
  3. Account role with CREATE DATABASE / SCHEMA / TABLE (or run sql/*.sql first)

Usage:
  python scripts/load_data.py              # DDL + load
  python scripts/load_data.py --ddl-only   # create objects only
  python scripts/load_data.py --load-only  # assume objects exist
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SQL_DIR = ROOT / "sql"

load_dotenv(ROOT / ".env")


def _require_env(keys: list[str]) -> dict[str, str]:
    missing = [k for k in keys if not os.getenv(k)]
    if missing:
        raise SystemExit(
            "Missing required environment variables: "
            + ", ".join(missing)
            + "\nCopy .env.example to .env and fill Snowflake credentials."
        )
    return {k: os.environ[k] for k in keys}


def connect():
    """Connect using password, externalbrowser SSO, or private key."""
    import snowflake.connector

    cfg = _require_env(
        [
            "SNOWFLAKE_ACCOUNT",
            "SNOWFLAKE_USER",
            "SNOWFLAKE_WAREHOUSE",
        ]
    )
    authenticator = (os.getenv("SNOWFLAKE_AUTHENTICATOR") or "password").strip().lower()
    password = os.getenv("SNOWFLAKE_PASSWORD")
    role = os.getenv("SNOWFLAKE_LOAD_ROLE") or os.getenv("SNOWFLAKE_ROLE")
    params = {
        "account": cfg["SNOWFLAKE_ACCOUNT"],
        "user": cfg["SNOWFLAKE_USER"],
        "warehouse": cfg["SNOWFLAKE_WAREHOUSE"],
        "database": os.getenv("SNOWFLAKE_DATABASE", "ANALYTICS_AI_DB"),
    }
    if role:
        params["role"] = role

    if authenticator in {"externalbrowser", "browser"}:
        # Opens a browser for SSO / Snowflake login — no password in .env
        params["authenticator"] = "externalbrowser"
    elif authenticator in {"snowflake", "password", ""}:
        if not password:
            raise SystemExit(
                "Set SNOWFLAKE_PASSWORD, or use SNOWFLAKE_AUTHENTICATOR=externalbrowser."
            )
        params["password"] = password
    else:
        raise SystemExit(
            f"Unsupported SNOWFLAKE_AUTHENTICATOR={authenticator!r}. "
            "Use 'password' or 'externalbrowser'."
        )
    return snowflake.connector.connect(**params)


def run_sql_file(cur, path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    # Split on semicolons; skip empty / comment-only chunks
    statements = []
    buf: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        buf.append(line)
        if stripped.endswith(";"):
            stmt = "\n".join(buf).strip().rstrip(";").strip()
            buf = []
            if stmt:
                statements.append(stmt)
    if buf:
        stmt = "\n".join(buf).strip().rstrip(";").strip()
        if stmt:
            statements.append(stmt)

    for stmt in statements:
        print(f"  SQL> {stmt.splitlines()[0][:100]}…")
        cur.execute(stmt)


def apply_ddl(conn) -> None:
    files = [
        SQL_DIR / "database.sql",
        SQL_DIR / "schemas.sql",
        SQL_DIR / "tables.sql",
    ]
    cur = conn.cursor()
    try:
        for path in files:
            print(f"Applying {path.name}")
            run_sql_file(cur, path)
        conn.commit()
    finally:
        cur.close()


def _load_csv(conn, table: str, csv_path: Path, columns: list[str]) -> int:
    from snowflake.connector.pandas_tools import write_pandas

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Missing {csv_path}. Run: python scripts/prepare_data.py"
        )
    df = pd.read_csv(csv_path)
    # Align to RAW VARCHAR columns (uppercase Snowflake identifiers)
    df = df[columns].copy()
    df.columns = [c.upper() for c in df.columns]
    df["_SOURCE_FILE"] = csv_path.name

    success, nchunks, nrows, _ = write_pandas(
        conn,
        df,
        table_name=table,
        database=os.getenv("SNOWFLAKE_DATABASE", "ANALYTICS_AI_DB"),
        schema="RAW",
        auto_create_table=False,
        overwrite=True,
        quote_identifiers=False,
    )
    if not success:
        raise RuntimeError(f"write_pandas failed for {table}")
    print(f"  Loaded {nrows:,} rows into RAW.{table} ({nchunks} chunk(s))")
    return int(nrows)


def load_raw(conn) -> None:
    cur = conn.cursor()
    try:
        cur.execute("USE DATABASE ANALYTICS_AI_DB")
        cur.execute("USE SCHEMA RAW")
    finally:
        cur.close()

    _load_csv(
        conn,
        "CUSTOMERS_RAW",
        DATA_DIR / "customers.csv",
        [
            "customer_id",
            "customer_name",
            "segment",
            "country",
            "state",
            "city",
            "postal_code",
            "region",
        ],
    )
    _load_csv(
        conn,
        "ORDERS_RAW",
        DATA_DIR / "orders.csv",
        [
            "order_id",
            "order_date",
            "ship_date",
            "ship_mode",
            "customer_id",
            "product_id",
            "quantity",
            "sales",
            "discount",
            "profit",
        ],
    )
    _load_csv(
        conn,
        "PRODUCTS_RAW",
        DATA_DIR / "products.csv",
        ["product_id", "product_name", "category", "sub_category"],
    )


def verify(conn) -> None:
    cur = conn.cursor()
    try:
        for table in ("CUSTOMERS_RAW", "ORDERS_RAW", "PRODUCTS_RAW"):
            cur.execute(f"SELECT COUNT(*) FROM ANALYTICS_AI_DB.RAW.{table}")
            n = cur.fetchone()[0]
            print(f"  RAW.{table}: {n:,} rows")
    finally:
        cur.close()


def apply_phase2_ddl(conn) -> None:
    cur = conn.cursor()
    try:
        for name in ("curated.sql", "analytics.sql", "views.sql"):
            path = SQL_DIR / name
            print(f"Applying {name}")
            run_sql_file(cur, path)
        conn.commit()
    finally:
        cur.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load Superstore RAW data into Snowflake")
    parser.add_argument("--ddl-only", action="store_true")
    parser.add_argument("--load-only", action="store_true")
    parser.add_argument(
        "--with-phase2",
        action="store_true",
        help="Also build CURATED + ANALYTICS marts after RAW load",
    )
    args = parser.parse_args(argv)

    print("Connecting to Snowflake…")
    conn = connect()
    try:
        if not args.load_only:
            print("Phase 1 DDL…")
            apply_ddl(conn)
        if not args.ddl_only:
            print("Phase 1 load RAW tables…")
            load_raw(conn)
            print("Verification…")
            verify(conn)
        if args.with_phase2 and not args.ddl_only:
            print("Phase 2 CURATED + ANALYTICS…")
            apply_phase2_ddl(conn)
        print("Snowflake load complete.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
