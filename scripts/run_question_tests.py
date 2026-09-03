#!/usr/bin/env python3
"""
Phase 13 — run the 25-question catalog.

Default: SQL-generation + validation only (no Snowflake).
Optional live mode executes against Snowflake and prints a pass/fail report.

Usage:
  python scripts/run_question_tests.py
  python scripts/run_question_tests.py --live
  python scripts/run_question_tests.py --live --limit 5
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.sql_generator import generate_sql_detailed  # noqa: E402
from src.sql_validator import validate_sql_detailed  # noqa: E402
from src.visualization import choose_visualization  # noqa: E402
from tests.question_catalog import get_question_catalog  # noqa: E402


def evaluate_case(case: dict, *, live: bool) -> dict:
    started = time.perf_counter()
    row = {
        "id": case["id"],
        "question": case["question"],
        "expected_tables": case.get("expected_tables"),
        "expected_metrics": case.get("expected_metrics"),
        "sql_characteristics": case.get("sql_contains"),
        "generated_sql": None,
        "row_count": None,
        "visualization_type": None,
        "execution_ms": None,
        "pass": False,
        "error": None,
    }

    gen = generate_sql_detailed(case["question"], provider="heuristic")
    row["generated_sql"] = gen.sql
    if gen.status != "ok":
        row["error"] = gen.error or gen.status
        row["execution_ms"] = (time.perf_counter() - started) * 1000
        return row

    val = validate_sql_detailed(gen.sql)
    if not val.ok:
        row["error"] = val.error
        row["execution_ms"] = (time.perf_counter() - started) * 1000
        return row

    upper = val.sql.upper()
    for token in case.get("sql_contains") or []:
        if token.upper() not in upper:
            row["error"] = f"Missing SQL token: {token}"
            row["execution_ms"] = (time.perf_counter() - started) * 1000
            return row

    if live:
        from src.query_executor import execute_query

        qres = execute_query(
            val.sql,
            user_question=case["question"],
            skip_validation=True,
            log_to_snowflake=True,
            visualization_type=case.get("expected_viz"),
        )
        row["execution_ms"] = qres.execution_time_ms
        if not qres.ok:
            row["error"] = qres.error
            return row
        row["row_count"] = qres.row_count
        if qres.dataframe is not None and not qres.dataframe.empty:
            row["visualization_type"] = choose_visualization(
                qres.dataframe, case["question"]
            )
    else:
        row["visualization_type"] = case.get("expected_viz")
        row["execution_ms"] = (time.perf_counter() - started) * 1000

    row["pass"] = True
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description="Run 25-question analytics eval")
    parser.add_argument("--live", action="store_true", help="Execute SQL on Snowflake")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of cases")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    cases = get_question_catalog()
    if args.limit > 0:
        cases = cases[: args.limit]

    results = [evaluate_case(c, live=args.live) for c in cases]
    passed = sum(1 for r in results if r["pass"])
    failed = len(results) - passed

    print(f"{'ID':>3}  {'PASS':<5}  QUESTION")
    print("-" * 72)
    for r in results:
        mark = "YES" if r["pass"] else "NO"
        print(f"{r['id']:>3}  {mark:<5}  {r['question']}")
        if not r["pass"]:
            print(f"       error: {r['error']}")
            if r.get("generated_sql"):
                print(f"       sql: {r['generated_sql'][:160]}…")

    print("-" * 72)
    print(f"Passed {passed}/{len(results)}  Failed {failed}")

    if args.json_out:
        args.json_out.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"Wrote {args.json_out}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
