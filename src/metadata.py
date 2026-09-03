"""Semantic metadata + glossary accessors (Phase 3).

Loads from Snowflake AI schema when connected; falls back to local constants
so the Streamlit app can still render prompts offline.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

# Preferred tables for NL→SQL (AI should prefer ANALYTICS marts)
RELATIONSHIPS = [
    {
        "from_table": "ANALYTICS_AI_DB.CURATED.CUSTOMERS",
        "from_column": "CUSTOMER_ID",
        "to_table": "ANALYTICS_AI_DB.CURATED.ORDERS",
        "to_column": "CUSTOMER_ID",
    },
    {
        "from_table": "ANALYTICS_AI_DB.CURATED.PRODUCTS",
        "from_column": "PRODUCT_ID",
        "to_table": "ANALYTICS_AI_DB.CURATED.ORDERS",
        "to_column": "PRODUCT_ID",
    },
    {
        "note": "Prefer ANALYTICS.SALES_ANALYTICS for most questions — already joined.",
    },
]

FALLBACK_GLOSSARY = {
    "Revenue": "SUM(sales)  -- or TOTAL_SALES on analytics marts",
    "Profit": "SUM(profit)  -- or TOTAL_PROFIT on analytics marts",
    "Quantity": "SUM(quantity)  -- or TOTAL_QUANTITY",
    "Order Count": "COUNT(DISTINCT order_id)  -- or ORDER_COUNT",
    "Customer Count": "COUNT(DISTINCT customer_id)",
    "Average Order Value": "SUM(sales) / NULLIF(COUNT(DISTINCT order_id), 0)",
    "Profit Margin": "SUM(profit) / NULLIF(SUM(sales), 0)",
}


def get_relationships() -> list[dict[str, Any]]:
    return list(RELATIONSHIPS)


def _fetch_all(sql: str) -> list[dict[str, Any]]:
    try:
        from snowflake_connection import get_connection
    except ImportError:
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parent))
        try:
            from snowflake_connection import get_connection  # type: ignore
        except Exception:
            return []

    try:
        conn = get_connection()
    except Exception:
        return []

    try:
        cur = conn.cursor()
        cur.execute(sql)
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        return rows
    except Exception:
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass


@lru_cache(maxsize=1)
def get_business_glossary() -> dict[str, str]:
    rows = _fetch_all(
        """
        SELECT TERM, DEFINITION_SQL, DESCRIPTION
        FROM ANALYTICS_AI_DB.AI.BUSINESS_GLOSSARY
        ORDER BY TERM
        """
    )
    if not rows:
        return dict(FALLBACK_GLOSSARY)
    return {
        r["TERM"]: f"{r['DEFINITION_SQL']}  -- {r.get('DESCRIPTION') or ''}".strip()
        for r in rows
    }


@lru_cache(maxsize=1)
def get_schema_metadata() -> dict[str, Any]:
    rows = _fetch_all(
        """
        SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE, DESCRIPTION, IS_KEY
        FROM ANALYTICS_AI_DB.AI.TABLE_METADATA
        ORDER BY TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME
        """
    )
    tables: dict[str, Any] = {}
    for r in rows:
        key = f"{r['TABLE_SCHEMA']}.{r['TABLE_NAME']}"
        entry = tables.setdefault(
            key,
            {"schema": r["TABLE_SCHEMA"], "table": r["TABLE_NAME"], "description": "", "columns": []},
        )
        if not r["COLUMN_NAME"]:
            entry["description"] = r["DESCRIPTION"]
        else:
            entry["columns"].append(
                {
                    "name": r["COLUMN_NAME"],
                    "type": r.get("DATA_TYPE"),
                    "description": r["DESCRIPTION"],
                    "is_key": bool(r.get("IS_KEY")),
                }
            )
    return tables


@lru_cache(maxsize=1)
def get_sample_questions() -> list[dict[str, Any]]:
    rows = _fetch_all(
        """
        SELECT CATEGORY, QUESTION, EXPECTED_TABLES, EXPECTED_METRIC, SORT_ORDER
        FROM ANALYTICS_AI_DB.AI.SAMPLE_QUESTIONS
        ORDER BY SORT_ORDER
        """
    )
    if rows:
        return rows
    # Local fallback matching UI defaults
    return [
        {"CATEGORY": "Revenue", "QUESTION": "What is total revenue?", "SORT_ORDER": 1},
        {"CATEGORY": "Revenue", "QUESTION": "Show monthly revenue trend", "SORT_ORDER": 2},
        {"CATEGORY": "Revenue", "QUESTION": "Show revenue by region", "SORT_ORDER": 3},
        {"CATEGORY": "Revenue", "QUESTION": "Show revenue by category", "SORT_ORDER": 4},
        {"CATEGORY": "Products", "QUESTION": "What are the top 10 products by revenue?", "SORT_ORDER": 5},
        {"CATEGORY": "Products", "QUESTION": "What are the top 10 products by profit?", "SORT_ORDER": 6},
        {"CATEGORY": "Products", "QUESTION": "Which products have negative profit?", "SORT_ORDER": 7},
        {"CATEGORY": "Customers", "QUESTION": "Who are the top 10 customers by revenue?", "SORT_ORDER": 8},
        {"CATEGORY": "Customers", "QUESTION": "Show revenue by customer segment", "SORT_ORDER": 9},
        {"CATEGORY": "Performance", "QUESTION": "Compare sales vs profit by category", "SORT_ORDER": 10},
        {"CATEGORY": "Performance", "QUESTION": "Show profit margin by category", "SORT_ORDER": 11},
        {"CATEGORY": "Performance", "QUESTION": "Show monthly sales growth", "SORT_ORDER": 12},
    ]


def format_metadata_for_prompt() -> str:
    """Compact text block for the SQL-generation LLM."""
    parts: list[str] = ["# Business glossary"]
    for term, definition in get_business_glossary().items():
        parts.append(f"- {term}: {definition}")

    parts.append("\n# Tables")
    for key, meta in get_schema_metadata().items():
        parts.append(f"\n## {key}")
        if meta.get("description"):
            parts.append(meta["description"])
        for col in meta.get("columns", []):
            key_flag = " [KEY]" if col.get("is_key") else ""
            parts.append(
                f"- {col['name']} ({col.get('type') or 'UNKNOWN'}){key_flag}: {col['description']}"
            )

    parts.append("\n# Relationships")
    for rel in get_relationships():
        if "note" in rel:
            parts.append(f"- NOTE: {rel['note']}")
        else:
            parts.append(
                f"- {rel['from_table']}.{rel['from_column']} → "
                f"{rel['to_table']}.{rel['to_column']}"
            )
    return "\n".join(parts)


def clear_metadata_cache() -> None:
    get_business_glossary.cache_clear()
    get_schema_metadata.cache_clear()
    get_sample_questions.cache_clear()
