"""Phase 6 — SQL validator tests."""

from __future__ import annotations

from src.sql_validator import validate_sql, validate_sql_detailed


def test_allows_simple_select():
    ok, sql, err = validate_sql(
        "SELECT SUM(SALES) AS TOTAL_REVENUE FROM ANALYTICS_AI_DB.ANALYTICS.SALES_ANALYTICS"
    )
    assert ok
    assert "SUM(SALES)" in sql
    assert err == ""


def test_allows_with_cte():
    ok, sql, err = validate_sql(
        """
        WITH r AS (
          SELECT REGION, SUM(SALES) AS REVENUE
          FROM ANALYTICS_AI_DB.ANALYTICS.SALES_ANALYTICS
          GROUP BY REGION
        )
        SELECT * FROM r ORDER BY REVENUE DESC
        """
    )
    assert ok
    assert sql.upper().startswith("WITH")


def test_strips_markdown_fences():
    ok, sql, err = validate_sql("```sql\nSELECT 1 AS N\n```")
    assert ok
    assert sql.upper().startswith("SELECT")


def test_rejects_insert():
    ok, sql, err = validate_sql("INSERT INTO T VALUES (1)")
    assert not ok
    assert sql == ""
    assert "INSERT" in err.upper()


def test_rejects_drop():
    ok, _, err = validate_sql("DROP TABLE ANALYTICS_AI_DB.ANALYTICS.SALES_ANALYTICS")
    assert not ok
    assert "DROP" in err.upper()


def test_rejects_update_delete_merge():
    for stmt in (
        "UPDATE T SET X=1",
        "DELETE FROM T",
        "MERGE INTO T USING S ON T.ID=S.ID WHEN MATCHED THEN UPDATE SET X=1",
        "TRUNCATE TABLE T",
        "ALTER TABLE T ADD COLUMN X INT",
        "CREATE TABLE T (ID INT)",
        "GRANT SELECT ON T TO ROLE R",
    ):
        ok, _, err = validate_sql(stmt)
        assert not ok, stmt
        assert err


def test_rejects_multiple_statements():
    ok, _, err = validate_sql("SELECT 1; SELECT 2")
    assert not ok
    assert "Multiple" in err


def test_rejects_insufficient_data():
    ok, _, err = validate_sql("INSUFFICIENT_DATA")
    assert not ok
    assert "INSUFFICIENT" in err.upper()


def test_adds_limit_to_detail_query():
    result = validate_sql_detailed(
        "SELECT PRODUCT_ID, PRODUCT_NAME FROM ANALYTICS_AI_DB.ANALYTICS.PRODUCT_ANALYTICS"
    )
    assert result.ok
    assert "LIMIT 100" in result.sql.upper()
    assert result.warnings


def test_does_not_add_limit_when_aggregated():
    ok, sql, _ = validate_sql(
        "SELECT REGION, SUM(SALES) AS R FROM ANALYTICS_AI_DB.ANALYTICS.SALES_ANALYTICS GROUP BY REGION"
    )
    assert ok
    assert "LIMIT" not in sql.upper()


def test_keeps_existing_limit():
    ok, sql, _ = validate_sql(
        "SELECT PRODUCT_ID FROM ANALYTICS_AI_DB.ANALYTICS.PRODUCT_ANALYTICS LIMIT 10"
    )
    assert ok
    assert sql.upper().count("LIMIT") == 1
    assert "LIMIT 10" in sql.upper()


def test_rejects_select_into():
    ok, _, err = validate_sql("SELECT * INTO NEW_TABLE FROM T")
    assert not ok
    assert "INTO" in err.upper()


def test_keyword_in_string_literal_allowed():
    ok, sql, err = validate_sql(
        "SELECT 'DELETE' AS WORD FROM ANALYTICS_AI_DB.ANALYTICS.SALES_ANALYTICS LIMIT 1"
    )
    assert ok, err
    assert "SELECT" in sql.upper()