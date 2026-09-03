"""Phase 8 — analytics pipeline unit tests."""

from __future__ import annotations

import pandas as pd

from src import analytics_pipeline as ap
from src.query_executor import QueryResult
from src.sql_generator import SqlGenerationResult


def test_empty_question():
    turn = ap.run_analytics_question("")
    assert not turn.ok
    assert turn.status == "error"


def test_insufficient_data(monkeypatch):
    monkeypatch.setattr(
        ap,
        "generate_sql_detailed",
        lambda *a, **k: SqlGenerationResult(
            sql="INSUFFICIENT_DATA", status="insufficient_data", provider="heuristic"
        ),
    )
    turn = ap.run_analytics_question("What is employee attrition?")
    assert not turn.ok
    assert turn.status == "insufficient_data"
    assert "not available" in turn.message.lower()


def test_success_path(monkeypatch):
    monkeypatch.setattr(
        ap,
        "generate_sql_detailed",
        lambda *a, **k: SqlGenerationResult(
            sql="SELECT SUM(SALES) AS TOTAL_REVENUE FROM ANALYTICS_AI_DB.ANALYTICS.SALES_ANALYTICS",
            status="ok",
            provider="heuristic",
            latency_ms=1.0,
        ),
    )
    monkeypatch.setattr(
        ap,
        "execute_query",
        lambda *a, **k: QueryResult(
            ok=True,
            sql=a[0],
            dataframe=pd.DataFrame({"TOTAL_REVENUE": [4201961.0]}),
            row_count=1,
            execution_time_ms=10.0,
        ),
    )
    turn = ap.run_analytics_question("What is total revenue?", log_to_snowflake=False)
    assert turn.ok
    assert turn.status == "success"
    assert turn.row_count == 1
    assert turn.dataframe is not None
    assert turn.insight
    assert "4201961" in turn.insight.replace(",", "")
    ctx = turn.context_blob()
    assert "TOTAL_REVENUE" in ctx["sql"] or "SALES" in ctx["sql"]
