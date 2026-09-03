"""Phase 5 — NL → SQL generation tests (heuristic provider, no LLM required)."""

from __future__ import annotations

from src.sql_generator import INSUFFICIENT, generate_sql, heuristic_sql


def test_total_revenue():
    sql = generate_sql("What is total revenue?", provider="heuristic")
    assert "SUM(SALES)" in sql.upper()
    assert "SALES_ANALYTICS" in sql.upper()


def test_top_products():
    sql = generate_sql("What are the top 10 products by revenue?", provider="heuristic")
    assert "PRODUCT_ANALYTICS" in sql.upper()
    assert "LIMIT 10" in sql.upper()
    assert "TOTAL_SALES" in sql.upper()


def test_revenue_by_region():
    sql = generate_sql("Show revenue by region", provider="heuristic")
    assert "GROUP BY REGION" in sql.upper()
    assert "SUM(SALES)" in sql.upper()


def test_negative_profit_products():
    sql = generate_sql("Which products have negative profit?", provider="heuristic")
    assert "TOTAL_PROFIT < 0" in sql.upper()


def test_average_order_value():
    sql = generate_sql("What is average order value?", provider="heuristic")
    assert "NULLIF" in sql.upper()
    assert "ORDER_ID" in sql.upper()


def test_insufficient_for_hr():
    sql = generate_sql("What is our employee attrition?", provider="heuristic")
    assert sql == INSUFFICIENT


def test_follow_up_their_profit():
    ctx = [
        {
            "question": "What are the top 10 products by revenue?",
            "sql": "SELECT ... FROM PRODUCT_ANALYTICS ORDER BY TOTAL_SALES DESC LIMIT 10",
            "result_summary": "top 10 products",
        }
    ]
    sql = generate_sql("Now show their profit.", conversation_context=ctx, provider="heuristic")
    assert "TOTAL_PROFIT" in sql.upper()
    assert "PRODUCT" in sql.upper()


def test_monthly_revenue():
    sql = heuristic_sql("Show monthly revenue trend")
    assert "ORDER_MONTH" in sql.upper()
    assert "GROUP BY ORDER_MONTH" in sql.upper()


def test_profit_margin_by_category():
    sql = heuristic_sql("Show profit margin by category")
    assert "PROFIT_MARGIN" in sql.upper()
    assert "NULLIF" in sql.upper()
