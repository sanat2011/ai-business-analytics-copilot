"""Phases 11–12 — default analytics + conversation context tests."""

from __future__ import annotations

from src.conversation import (
    build_conversation_context,
    infer_entity_from_question,
    is_follow_up,
    resolve_follow_up_entity,
)
from src.default_analytics import (
    CATEGORY_ORDER,
    get_default_analytics,
    get_default_analytics_by_category,
)
from src.sql_generator import generate_sql


def test_twelve_default_analytics():
    items = get_default_analytics()
    assert len(items) == 12
    assert [i["sort_order"] for i in items] == list(range(1, 13))
    cats = get_default_analytics_by_category()
    assert list(cats.keys()) == CATEGORY_ORDER


def test_defaults_generate_sql():
    for item in get_default_analytics():
        sql = generate_sql(item["question"], provider="heuristic")
        assert sql != "INSUFFICIENT_DATA", item["question"]
        assert "SELECT" in sql.upper()
        assert "ANALYTICS_AI_DB" in sql.upper()


def test_follow_up_their_profit():
    ctx = [
        {
            "question": "What are the top 10 products by revenue?",
            "sql": "SELECT ...",
            "result_summary": "top products",
            "entity": "products",
        }
    ]
    sql = generate_sql("Now show their profit.", conversation_context=ctx, provider="heuristic")
    assert "TOTAL_PROFIT" in sql.upper()
    assert "PRODUCT" in sql.upper()


def test_follow_up_region_profit():
    ctx = [
        {
            "question": "Show revenue by region",
            "sql": "SELECT REGION, SUM(SALES)...",
            "entity": "regions",
        }
    ]
    sql = generate_sql("Show their profit.", conversation_context=ctx, provider="heuristic")
    assert "REGION" in sql.upper()
    assert "PROFIT" in sql.upper()


def test_conversation_helpers():
    assert infer_entity_from_question("top 10 products by revenue") == "products"
    assert is_follow_up("Now show their profit.")
    messages = [
        {"role": "user", "content": "q"},
        {
            "role": "assistant",
            "turn": {
                "question": "What are the top 10 products by revenue?",
                "sql": "SELECT 1",
                "result_summary": "ok",
                "row_count": 10,
            },
        },
    ]
    ctx = build_conversation_context(messages)
    assert len(ctx) == 1
    assert ctx[0]["entity"] == "products"
    assert resolve_follow_up_entity("their profit", ctx) == "products"


def test_monthly_sales_growth_sql():
    sql = generate_sql("Show monthly sales growth", provider="heuristic")
    assert "MOM_GROWTH" in sql.upper() or "LAG" in sql.upper()
