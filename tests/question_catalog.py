"""
Phase 13 — curated evaluation questions (spec §21).

Each case defines expectations for NL→SQL quality without requiring live Snowflake.
Optional live execution is handled by scripts/run_question_tests.py.
"""

from __future__ import annotations

from typing import Any

# Fully-qualified mart names used in assertions
SALES = "SALES_ANALYTICS"
CUSTOMERS = "CUSTOMER_ANALYTICS"
PRODUCTS = "PRODUCT_ANALYTICS"

QUESTION_CATALOG: list[dict[str, Any]] = [
    {
        "id": 1,
        "question": "What is total revenue?",
        "expected_tables": [SALES],
        "expected_metrics": ["SALES", "REVENUE"],
        "sql_contains": ["SUM(SALES)", SALES],
        "sql_not_contains": ["INSERT", "DELETE"],
        "expected_viz": "kpi",
    },
    {
        "id": 2,
        "question": "What is total profit?",
        "expected_tables": [SALES],
        "expected_metrics": ["PROFIT"],
        "sql_contains": ["SUM(PROFIT)", SALES],
        "expected_viz": "kpi",
    },
    {
        "id": 3,
        "question": "What are the top 5 products by revenue?",
        "expected_tables": [PRODUCTS],
        "expected_metrics": ["TOTAL_SALES", "SALES"],
        "sql_contains": [PRODUCTS, "ORDER BY", "LIMIT"],
        "expected_viz": "bar",
    },
    {
        "id": 4,
        "question": "What are the top 5 products by profit?",
        "expected_tables": [PRODUCTS],
        "expected_metrics": ["TOTAL_PROFIT", "PROFIT"],
        "sql_contains": [PRODUCTS, "TOTAL_PROFIT", "LIMIT"],
        "expected_viz": "bar",
    },
    {
        "id": 5,
        "question": "Show revenue by region.",
        "expected_tables": [SALES],
        "expected_metrics": ["SALES", "REVENUE"],
        "sql_contains": ["REGION", "GROUP BY", "SUM(SALES)"],
        "expected_viz": "bar",
    },
    {
        "id": 6,
        "question": "Show profit by region.",
        "expected_tables": [SALES],
        "expected_metrics": ["PROFIT"],
        "sql_contains": ["REGION", "GROUP BY", "SUM(PROFIT)"],
        "expected_viz": "bar",
    },
    {
        "id": 7,
        "question": "Show monthly revenue.",
        "expected_tables": [SALES],
        "expected_metrics": ["SALES", "REVENUE"],
        "sql_contains": ["ORDER_MONTH", "GROUP BY", "SUM(SALES)"],
        "expected_viz": "line",
    },
    {
        "id": 8,
        "question": "Show monthly profit.",
        "expected_tables": [SALES],
        "expected_metrics": ["PROFIT"],
        "sql_contains": ["ORDER_MONTH", "GROUP BY", "SUM(PROFIT)"],
        "expected_viz": "line",
    },
    {
        "id": 9,
        "question": "Which category has the highest revenue?",
        "expected_tables": [SALES],
        "expected_metrics": ["SALES", "REVENUE"],
        "sql_contains": ["CATEGORY", "GROUP BY", "SUM(SALES)"],
        "expected_viz": "bar",
    },
    {
        "id": 10,
        "question": "Which category has the highest profit?",
        "expected_tables": [SALES],
        "expected_metrics": ["PROFIT"],
        "sql_contains": ["CATEGORY", "GROUP BY", "SUM(PROFIT)"],
        "expected_viz": "bar",
    },
    {
        "id": 11,
        "question": "Which products have negative profit?",
        "expected_tables": [PRODUCTS],
        "expected_metrics": ["PROFIT"],
        "sql_contains": [PRODUCTS, "TOTAL_PROFIT < 0"],
        "expected_viz": "table",
    },
    {
        "id": 12,
        "question": "What is average order value?",
        "expected_tables": [SALES],
        "expected_metrics": ["AOV", "SALES", "ORDER"],
        "sql_contains": ["NULLIF", "ORDER_ID", "SUM(SALES)"],
        "expected_viz": "kpi",
    },
    {
        "id": 13,
        "question": "What is revenue by customer segment?",
        "expected_tables": [SALES],
        "expected_metrics": ["SALES", "REVENUE"],
        "sql_contains": ["SEGMENT", "GROUP BY", "SUM(SALES)"],
        "expected_viz": "bar",
    },
    {
        "id": 14,
        "question": "Who are the top 10 customers?",
        "expected_tables": [CUSTOMERS],
        "expected_metrics": ["TOTAL_SALES", "SALES"],
        "sql_contains": [CUSTOMERS, "LIMIT 10", "ORDER BY"],
        "expected_viz": "bar",
    },
    {
        "id": 15,
        "question": "Which state has the highest revenue?",
        "expected_tables": [SALES],
        "expected_metrics": ["SALES", "REVENUE"],
        "sql_contains": ["STATE", "GROUP BY", "SUM(SALES)"],
        "expected_viz": "bar",
    },
    {
        "id": 16,
        "question": "Show revenue by sub-category.",
        "expected_tables": [SALES],
        "expected_metrics": ["SALES", "REVENUE"],
        "sql_contains": ["SUB_CATEGORY", "GROUP BY", "SUM(SALES)"],
        "expected_viz": "bar",
    },
    {
        "id": 17,
        "question": "Compare revenue by year.",
        "expected_tables": [SALES],
        "expected_metrics": ["SALES", "REVENUE"],
        "sql_contains": ["ORDER_YEAR", "GROUP BY", "SUM(SALES)"],
        "expected_viz": "bar",
    },
    {
        "id": 18,
        "question": "Compare profit by year.",
        "expected_tables": [SALES],
        "expected_metrics": ["PROFIT"],
        "sql_contains": ["ORDER_YEAR", "GROUP BY", "SUM(PROFIT)"],
        "expected_viz": "bar",
    },
    {
        "id": 19,
        "question": "Show profit margin by category.",
        "expected_tables": [SALES],
        "expected_metrics": ["PROFIT_MARGIN", "MARGIN"],
        "sql_contains": ["PROFIT_MARGIN", "NULLIF", "CATEGORY"],
        "expected_viz": "bar",
    },
    {
        "id": 20,
        "question": "Which region has the highest profit margin?",
        "expected_tables": [SALES],
        "expected_metrics": ["PROFIT_MARGIN", "MARGIN"],
        "sql_contains": ["REGION", "PROFIT_MARGIN", "NULLIF"],
        "expected_viz": "bar",
    },
    {
        "id": 21,
        "question": "Show the top 10 products by quantity.",
        "expected_tables": [PRODUCTS],
        "expected_metrics": ["QUANTITY"],
        "sql_contains": [PRODUCTS, "TOTAL_QUANTITY", "LIMIT 10"],
        "expected_viz": "bar",
    },
    {
        "id": 21b,
        "question": "Provide all products available",
        "expected_tables": [PRODUCTS],
        "expected_metrics": ["PRODUCT_NAME"],
        "sql_contains": [PRODUCTS, "PRODUCT_NAME", "CATEGORY"],
        "expected_viz": "table",
    },
    {
        "id": 22,
        "question": "Which category has the highest quantity?",
        "expected_tables": [SALES],
        "expected_metrics": ["QUANTITY"],
        "sql_contains": ["CATEGORY", "SUM(QUANTITY)", "GROUP BY"],
        "expected_viz": "bar",
    },
    {
        "id": 23,
        "question": "Show sales trend over time.",
        "expected_tables": [SALES],
        "expected_metrics": ["SALES", "REVENUE"],
        "sql_contains": ["ORDER_MONTH", "SUM(SALES)"],
        "expected_viz": "line",
    },
    {
        "id": 24,
        "question": "Which customers have the highest sales?",
        "expected_tables": [CUSTOMERS],
        "expected_metrics": ["TOTAL_SALES", "SALES"],
        "sql_contains": [CUSTOMERS, "TOTAL_SALES", "ORDER BY"],
        "expected_viz": "bar",
    },
    {
        "id": 25,
        "question": "Show revenue contribution by category.",
        "expected_tables": [SALES],
        "expected_metrics": ["SALES", "PCT", "REVENUE"],
        "sql_contains": ["CATEGORY", "SUM(SALES)", "PCT_OF_SALES"],
        "expected_viz": "pie",
    },
]


def get_question_catalog() -> list[dict[str, Any]]:
    return list(QUESTION_CATALOG)
