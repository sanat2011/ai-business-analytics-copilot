"""Phase 7 — query executor unit tests (validation path; no live Snowflake required)."""

from __future__ import annotations

import pandas as pd

from src import query_executor as qe


def test_rejects_destructive_sql_before_execution():
    result = qe.execute_query("DROP TABLE T", log_to_snowflake=False)
    assert not result.ok
    assert "DROP" in (result.error or "").upper()
    assert result.dataframe is None


def test_rejects_insufficient_data():
    result = qe.execute_query("INSUFFICIENT_DATA", log_to_snowflake=False)
    assert not result.ok


def test_execute_uses_session_when_valid(monkeypatch):
    called = {}

    class FakeSession:
        def sql(self, sql):
            called["sql"] = sql

            class FakeDF:
                def to_pandas(self):
                    return pd.DataFrame({"TOTAL_REVENUE": [123.45]})

            return FakeDF()

    result = qe.execute_query(
        "SELECT SUM(SALES) AS TOTAL_REVENUE FROM ANALYTICS_AI_DB.ANALYTICS.SALES_ANALYTICS",
        user_question="What is total revenue?",
        log_to_snowflake=False,
        session=FakeSession(),
    )
    assert result.ok
    assert result.row_count == 1
    assert result.dataframe is not None
    assert float(result.dataframe.iloc[0]["TOTAL_REVENUE"]) == 123.45
    assert "SUM(SALES)" in called["sql"].upper()


def test_empty_result_flag(monkeypatch):
    class FakeSession:
        def sql(self, sql):
            class FakeDF:
                def to_pandas(self):
                    return pd.DataFrame(columns=["REGION", "TOTAL_REVENUE"])

            return FakeDF()

    result = qe.execute_query(
        "SELECT REGION, SUM(SALES) AS TOTAL_REVENUE FROM ANALYTICS_AI_DB.ANALYTICS.SALES_ANALYTICS GROUP BY REGION HAVING 1=0",
        log_to_snowflake=False,
        session=FakeSession(),
    )
    assert result.ok
    assert result.empty
    assert result.row_count == 0


def test_execution_error_is_captured():
    class FakeSession:
        def sql(self, sql):
            raise RuntimeError("Object does not exist: SALES_ANALYTICS")

    result = qe.execute_query(
        "SELECT 1 AS N",
        log_to_snowflake=False,
        session=FakeSession(),
    )
    assert not result.ok
    assert "missing" in (result.error or "").lower() or "exist" in (result.error or "").lower()


def test_summary_on_success():
    class FakeSession:
        def sql(self, sql):
            class FakeDF:
                def to_pandas(self):
                    return pd.DataFrame({"REGION": ["West", "East"], "TOTAL_REVENUE": [1, 2]})

            return FakeDF()

    result = qe.execute_query(
        "SELECT REGION, SUM(SALES) AS TOTAL_REVENUE FROM ANALYTICS_AI_DB.ANALYTICS.SALES_ANALYTICS GROUP BY REGION",
        log_to_snowflake=False,
        session=FakeSession(),
    )
    text = result.summary()
    assert "2 rows" in text
    assert "West" in text
