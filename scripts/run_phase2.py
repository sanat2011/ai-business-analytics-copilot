#!/usr/bin/env python3
"""
Phase 2 — Build CURATED entities + ANALYTICS marts from RAW.

Prerequisites:
  Phase 1 RAW tables loaded (CUSTOMERS_RAW, ORDERS_RAW, PRODUCTS_RAW)

Usage:
  python scripts/run_phase2.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Reuse Phase 1 connection + SQL runner
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from load_data import apply_ddl, connect, run_sql_file  # noqa: E402


def apply_phase2(conn) -> None:
    cur = conn.cursor()
    try:
        for name in ("curated.sql", "analytics.sql", "views.sql"):
            path = ROOT / "sql" / name
            print(f"Applying {name}")
            run_sql_file(cur, path)
        conn.commit()
    finally:
        cur.close()


def verify(conn) -> None:
    cur = conn.cursor()
    checks = [
        ("CURATED.CUSTOMERS", "SELECT COUNT(*) FROM ANALYTICS_AI_DB.CURATED.CUSTOMERS"),
        ("CURATED.ORDERS", "SELECT COUNT(*) FROM ANALYTICS_AI_DB.CURATED.ORDERS"),
        ("CURATED.PRODUCTS", "SELECT COUNT(*) FROM ANALYTICS_AI_DB.CURATED.PRODUCTS"),
        ("ANALYTICS.SALES_ANALYTICS", "SELECT COUNT(*) FROM ANALYTICS_AI_DB.ANALYTICS.SALES_ANALYTICS"),
        ("ANALYTICS.CUSTOMER_ANALYTICS", "SELECT COUNT(*) FROM ANALYTICS_AI_DB.ANALYTICS.CUSTOMER_ANALYTICS"),
        ("ANALYTICS.PRODUCT_ANALYTICS", "SELECT COUNT(*) FROM ANALYTICS_AI_DB.ANALYTICS.PRODUCT_ANALYTICS"),
    ]
    try:
        for label, sql in checks:
            cur.execute(sql)
            print(f"  {label}: {cur.fetchone()[0]:,} rows")
        cur.execute(
            """
            SELECT
                ROUND(SUM(SALES), 2) AS REVENUE,
                ROUND(SUM(PROFIT), 2) AS PROFIT
            FROM ANALYTICS_AI_DB.ANALYTICS.SALES_ANALYTICS
            """
        )
        revenue, profit = cur.fetchone()
        print(f"  Totals → revenue={revenue}, profit={profit}")
    finally:
        cur.close()


def main() -> int:
    print("Connecting to Snowflake…")
    conn = connect()
    try:
        print("Phase 2 transforms…")
        apply_phase2(conn)
        print("Verification…")
        verify(conn)
        print("Phase 2 complete.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
