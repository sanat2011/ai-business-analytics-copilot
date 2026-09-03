#!/usr/bin/env python3
"""Phase 5 — smoke-test NL→SQL for sample questions."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.sql_generator import generate_sql_detailed  # noqa: E402

QUESTIONS = [
    "What is total revenue?",
    "What are the top 10 products by revenue?",
    "Show revenue by region",
    "What is our employee attrition?",
]


def main() -> int:
    provider = "heuristic"
    if len(sys.argv) > 1:
        provider = sys.argv[1]
    for q in QUESTIONS:
        result = generate_sql_detailed(q, provider=provider)
        print(f"Q: {q}")
        print(f"  provider={result.provider} status={result.status} ({result.latency_ms:.0f} ms)")
        print(f"  SQL: {result.sql[:200]}")
        if result.error:
            print(f"  error: {result.error}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
