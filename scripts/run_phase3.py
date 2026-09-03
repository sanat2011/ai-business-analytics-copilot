#!/usr/bin/env python3
"""Phase 3 — Load AI glossary, table metadata, and sample questions."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from load_data import connect, run_sql_file  # noqa: E402


def main() -> int:
    print("Connecting to Snowflake…")
    conn = connect()
    cur = conn.cursor()
    try:
        print("Applying metadata.sql…")
        run_sql_file(cur, ROOT / "sql" / "metadata.sql")
        conn.commit()
        checks = [
            ("BUSINESS_GLOSSARY", "SELECT COUNT(*) FROM ANALYTICS_AI_DB.AI.BUSINESS_GLOSSARY"),
            ("TABLE_METADATA", "SELECT COUNT(*) FROM ANALYTICS_AI_DB.AI.TABLE_METADATA"),
            ("SAMPLE_QUESTIONS", "SELECT COUNT(*) FROM ANALYTICS_AI_DB.AI.SAMPLE_QUESTIONS"),
        ]
        for label, sql in checks:
            cur.execute(sql)
            print(f"  AI.{label}: {cur.fetchone()[0]:,} rows")
        print("Phase 3 complete.")
    finally:
        cur.close()
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
