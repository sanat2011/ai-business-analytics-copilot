"""LLM prompt templates (Phase 5 / 10)."""

from __future__ import annotations

from typing import Any

SQL_SYSTEM_PROMPT = """You are an enterprise business analytics SQL assistant.

Your job is to convert a user's natural-language business question into a valid Snowflake SELECT query.

You have access only to the tables, columns, relationships and business definitions provided below.

Rules:
1. Use only tables and columns provided in the metadata.
2. Never invent a column.
3. Never invent a table.
4. Use the documented business definitions.
5. Use the documented relationships for joins.
6. Generate SELECT statements only.
7. Never generate INSERT.
8. Never generate UPDATE.
9. Never generate DELETE.
10. Never generate DROP.
11. Never generate ALTER.
12. Never generate TRUNCATE.
13. Do not modify Snowflake data.
14. Use Snowflake SQL syntax.
15. Add reasonable LIMIT clauses for detail queries.
16. Avoid SELECT * unless explicitly required.
17. Prefer explicit column names.
18. Use NULLIF when required to avoid division-by-zero.
19. For percentage calculations, clearly define the denominator.
20. If the requested information cannot be answered from the provided metadata, return INSUFFICIENT_DATA.
21. Return SQL only, without markdown formatting.
22. Prefer fully qualified names: ANALYTICS_AI_DB.ANALYTICS.SALES_ANALYTICS (and sibling marts).
23. Prefer ANALYTICS.SALES_ANALYTICS / CUSTOMER_ANALYTICS / PRODUCT_ANALYTICS over CURATED joins when possible.
24. For revenue use SUM(SALES) or TOTAL_SALES; for profit use SUM(PROFIT) or TOTAL_PROFIT.
25. Questions like "list all products", "products available", or "product catalog" MUST query
    ANALYTICS_AI_DB.ANALYTICS.PRODUCT_ANALYTICS (PRODUCT_ID, PRODUCT_NAME, CATEGORY, SUB_CATEGORY, …)
    with ORDER BY CATEGORY, PRODUCT_NAME and LIMIT 500 — do NOT return INSUFFICIENT_DATA for product lists.
"""

INSIGHT_SYSTEM_PROMPT = """You are a business analyst. Write 2–4 sentences of insight
using ONLY numbers present in the provided result. Do not invent facts or predictions.
"""


def build_sql_user_prompt(
    user_question: str,
    schema_metadata: str,
    business_glossary: dict[str, str] | str,
    relationships: list[dict[str, Any]] | str,
    conversation_context: list[dict[str, Any]] | None = None,
) -> str:
    if isinstance(business_glossary, dict):
        glossary_txt = "\n".join(f"- {k}: {v}" for k, v in business_glossary.items())
    else:
        glossary_txt = str(business_glossary)

    if isinstance(relationships, list):
        rel_lines = []
        for rel in relationships:
            if "note" in rel:
                rel_lines.append(f"- NOTE: {rel['note']}")
            else:
                rel_lines.append(
                    f"- {rel.get('from_table')}.{rel.get('from_column')} → "
                    f"{rel.get('to_table')}.{rel.get('to_column')}"
                )
        relationships_txt = "\n".join(rel_lines)
    else:
        relationships_txt = str(relationships)

    context_txt = "(none)"
    if conversation_context:
        bits = []
        for turn in conversation_context[-4:]:
            q = turn.get("question") or turn.get("user_question") or ""
            sql = turn.get("sql") or turn.get("generated_sql") or ""
            summary = turn.get("result_summary") or ""
            bits.append(f"Q: {q}\nSQL: {sql}\nSummary: {summary}")
        context_txt = "\n---\n".join(bits)

    return f"""Business definitions:
{glossary_txt}

Database schema and metadata:
{schema_metadata}

Relationships:
{relationships_txt}

Conversation context (for follow-ups like "their"):
{context_txt}

User question:
{user_question}

Generate the safest valid Snowflake SELECT statement.
Return SQL only, or INSUFFICIENT_DATA.
"""


def build_full_sql_prompt(
    user_question: str,
    schema_metadata: str,
    business_glossary: dict[str, str] | str,
    relationships: list[dict[str, Any]] | str,
    conversation_context: list[dict[str, Any]] | None = None,
) -> str:
    """Single string prompt for providers that do not support chat roles (Cortex COMPLETE)."""
    user = build_sql_user_prompt(
        user_question,
        schema_metadata,
        business_glossary,
        relationships,
        conversation_context,
    )
    return f"{SQL_SYSTEM_PROMPT}\n\n{user}"
