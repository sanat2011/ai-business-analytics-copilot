"""Phase 13 — 25-question NL→SQL evaluation harness."""

from __future__ import annotations

import pandas as pd
import pytest

from src.sql_generator import generate_sql
from src.sql_validator import validate_sql
from src.visualization import choose_visualization
from tests.question_catalog import QUESTION_CATALOG, get_question_catalog


def _assert_sql_case(case: dict) -> dict:
    question = case["question"]
    sql = generate_sql(question, provider="heuristic")
    upper = sql.upper()

    assert sql != "INSUFFICIENT_DATA", f"INSUFFICIENT_DATA for: {question}"
    assert "SELECT" in upper

    for token in case.get("sql_contains") or []:
        assert token.upper() in upper, f"Expected '{token}' in SQL for: {question}\nSQL:\n{sql}"

    for token in case.get("sql_not_contains") or []:
        assert token.upper() not in upper, f"Unexpected '{token}' in SQL for: {question}"

    # Expected tables: at least one must appear
    tables = case.get("expected_tables") or []
    if tables:
        assert any(t.upper() in upper for t in tables), (
            f"None of {tables} found in SQL for: {question}\nSQL:\n{sql}"
        )

    # Metrics: at least one keyword should appear
    metrics = case.get("expected_metrics") or []
    if metrics:
        assert any(m.upper() in upper for m in metrics), (
            f"None of metrics {metrics} found for: {question}\nSQL:\n{sql}"
        )

    ok, safe_sql, err = validate_sql(sql)
    assert ok, f"Validation failed for: {question}: {err}"

    return {"question": question, "sql": safe_sql, "pass": True}


@pytest.mark.parametrize("case", QUESTION_CATALOG, ids=lambda c: f"{c['id']:02d}")
def test_question_sql_characteristics(case: dict):
    _assert_sql_case(case)


def test_catalog_has_at_least_25():
    assert len(get_question_catalog()) >= 25


def test_destructive_still_rejected():
    ok, _, err = validate_sql("DROP TABLE ANALYTICS_AI_DB.ANALYTICS.SALES_ANALYTICS")
    assert not ok
    assert "DROP" in err.upper()


def test_viz_expectations_smoke():
    """Lightweight viz checks using synthetic frames matching each expected type."""
    samples = {
        "kpi": pd.DataFrame({"TOTAL_REVENUE": [1.0]}),
        "line": pd.DataFrame(
            {
                "ORDER_MONTH": pd.date_range("2024-01-01", periods=4, freq="MS"),
                "REVENUE": [1, 2, 3, 4],
            }
        ),
        "bar": pd.DataFrame({"REGION": ["W", "E"], "TOTAL_REVENUE": [2, 1]}),
        "pie": pd.DataFrame({"CATEGORY": ["A", "B"], "PCT_OF_SALES": [0.6, 0.4]}),
        "table": pd.DataFrame(
            {"PRODUCT_NAME": [f"P{i}" for i in range(60)], "TOTAL_SALES": list(range(60))}
        ),
    }
    for case in QUESTION_CATALOG:
        expected = case.get("expected_viz")
        if not expected or expected not in samples:
            continue
        got = choose_visualization(samples[expected], case["question"])
        assert got == expected, f"id={case['id']} expected viz {expected}, got {got}"
