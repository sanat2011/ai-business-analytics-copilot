"""
NL → SQL generation (Phase 5).

Providers (in order of preference when LLM_PROVIDER=auto/default):
  1. snowflake_cortex — SNOWFLAKE.CORTEX.COMPLETE via Snowpark session
  2. openai — OpenAI Chat Completions (optional OPENAI_API_KEY)
  3. heuristic — deterministic templates for common retail questions (offline MVP)

Never invent tables/columns outside the provided metadata contract.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any

from src.prompts import SQL_SYSTEM_PROMPT, build_full_sql_prompt, build_sql_user_prompt


@dataclass
class SqlGenerationResult:
    sql: str
    status: str  # ok | insufficient_data | error
    provider: str
    latency_ms: float = 0.0
    raw_response: str = ""
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


INSUFFICIENT = "INSUFFICIENT_DATA"

# Topics we cannot answer from Superstore analytics
UNSUPPORTED_PATTERNS = [
    r"\bemployee\b",
    r"\battrition\b",
    r"\bpayroll\b",
    r"\bsalary\b",
    r"\binventory\b",
    r"\bweather\b",
    r"\bhr\b",
]


def _strip_sql_fences(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:sql)?\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\s*```$", "", t)
    return t.strip().rstrip(";")


def _normalize_llm_sql(text: str) -> str:
    t = _strip_sql_fences(text)
    # Some models prepend "SQL:" or explanations — keep from first SELECT/WITH
    upper = t.upper()
    if "INSUFFICIENT_DATA" in upper and "SELECT" not in upper and "WITH" not in upper:
        return INSUFFICIENT
    for marker in ("SELECT", "WITH"):
        idx = upper.find(marker)
        if idx >= 0:
            return t[idx:].strip().rstrip(";")
    return t.strip().rstrip(";")


def _provider_name() -> str:
    return (os.getenv("LLM_PROVIDER") or "snowflake_cortex").strip().lower()


def _cortex_model() -> str:
    return os.getenv("CORTEX_MODEL") or "mistral-large"


def _openai_model() -> str:
    return os.getenv("OPENAI_MODEL") or "gpt-4o-mini"


def _question_unsupported(question: str) -> bool:
    q = question.lower()
    return any(re.search(p, q) for p in UNSUPPORTED_PATTERNS)


def _format_metadata_block(metadata: dict[str, Any] | None) -> tuple[str, dict, list]:
    """Accept either pre-built dict from caller or load from src.metadata."""
    if metadata and metadata.get("schema_text"):
        return (
            str(metadata["schema_text"]),
            metadata.get("glossary") or {},
            metadata.get("relationships") or [],
        )

    from src.metadata import (
        format_metadata_for_prompt,
        get_business_glossary,
        get_relationships,
        get_schema_metadata,
    )

    if metadata and metadata.get("tables"):
        # Caller passed get_schema_metadata()-like structure
        parts = []
        for key, meta in metadata["tables"].items():
            parts.append(f"\n## {key}")
            if meta.get("description"):
                parts.append(meta["description"])
            for col in meta.get("columns", []):
                parts.append(
                    f"- {col['name']} ({col.get('type') or 'UNKNOWN'}): {col['description']}"
                )
        schema_text = "\n".join(parts)
        glossary = metadata.get("glossary") or get_business_glossary()
        relationships = metadata.get("relationships") or get_relationships()
        return schema_text, glossary, relationships

    return format_metadata_for_prompt(), get_business_glossary(), get_relationships()


def _call_cortex(prompt: str) -> str:
    from src.snowflake_connection import get_session

    session = get_session()
    model = _cortex_model()
    rows = session.sql(
        "SELECT SNOWFLAKE.CORTEX.COMPLETE(?, ?) AS RESP",
        params=(model, prompt),
    ).collect()
    return rows[0]["RESP"] if rows else ""


def _call_openai(prompt_user: str) -> str:
    import json
    import urllib.request

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    body = {
        "model": _openai_model(),
        "temperature": 0,
        "messages": [
            {"role": "system", "content": SQL_SYSTEM_PROMPT},
            {"role": "user", "content": prompt_user},
        ],
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload["choices"][0]["message"]["content"]


def heuristic_sql(
    user_question: str,
    conversation_context: list[dict[str, Any]] | None = None,
) -> str:
    """
    Deterministic SQL for common Superstore questions.
    Used as offline fallback and for unit tests without LLM keys.
    """
    q = (user_question or "").strip().lower()
    sales = "ANALYTICS_AI_DB.ANALYTICS.SALES_ANALYTICS"
    customers = "ANALYTICS_AI_DB.ANALYTICS.CUSTOMER_ANALYTICS"
    products = "ANALYTICS_AI_DB.ANALYTICS.PRODUCT_ANALYTICS"

    # Follow-ups referring to prior ranked entities ("their profit", "now show sales")
    if conversation_context:
        from src.conversation import resolve_follow_up_entity

        entity = resolve_follow_up_entity(user_question, conversation_context)
        prev = conversation_context[-1]
        prev_q = (prev.get("question") or prev.get("user_question") or "").lower()
        wants_profit = "profit" in q and "margin" not in q
        wants_sales = any(w in q for w in ("sales", "revenue")) and "profit" not in q
        wants_qty = "quantity" in q or "units" in q
        refers = bool(re.search(r"\b(their|those|these|them|same|previous)\b", q)) or bool(
            re.match(r"^(now |and |also |what about |how about )", q)
        )

        if entity == "products" or ("product" in prev_q and refers):
            if wants_profit:
                return f"""
SELECT PRODUCT_ID, PRODUCT_NAME, TOTAL_SALES, TOTAL_PROFIT
FROM {products}
ORDER BY TOTAL_SALES DESC
LIMIT 10
""".strip()
            if wants_qty:
                return f"""
SELECT PRODUCT_ID, PRODUCT_NAME, TOTAL_QUANTITY, TOTAL_SALES
FROM {products}
ORDER BY TOTAL_SALES DESC
LIMIT 10
""".strip()
            if wants_sales or refers:
                return f"""
SELECT PRODUCT_ID, PRODUCT_NAME, TOTAL_SALES, TOTAL_PROFIT
FROM {products}
ORDER BY TOTAL_SALES DESC
LIMIT 10
""".strip()

        if entity == "customers" or ("customer" in prev_q and refers):
            if wants_profit:
                return f"""
SELECT CUSTOMER_ID, CUSTOMER_NAME, TOTAL_SALES, TOTAL_PROFIT
FROM {customers}
ORDER BY TOTAL_SALES DESC
LIMIT 10
""".strip()
            return f"""
SELECT CUSTOMER_ID, CUSTOMER_NAME, TOTAL_SALES, TOTAL_PROFIT
FROM {customers}
ORDER BY TOTAL_SALES DESC
LIMIT 10
""".strip()

        if entity == "regions" or ("region" in prev_q and refers):
            metric = "PROFIT" if wants_profit else "SALES"
            alias = "TOTAL_PROFIT" if wants_profit else "TOTAL_REVENUE"
            return f"""
SELECT REGION, SUM({metric}) AS {alias}
FROM {sales}
GROUP BY REGION
ORDER BY {alias} DESC
""".strip()

        if entity == "categories" or ("categor" in prev_q and refers):
            if "margin" in q:
                return f"""
SELECT CATEGORY,
       SUM(PROFIT) / NULLIF(SUM(SALES), 0) AS PROFIT_MARGIN
FROM {sales}
GROUP BY CATEGORY
ORDER BY PROFIT_MARGIN DESC
""".strip()
            metric = "PROFIT" if wants_profit else "SALES"
            alias = "TOTAL_PROFIT" if wants_profit else "TOTAL_REVENUE"
            return f"""
SELECT CATEGORY, SUM({metric}) AS {alias}
FROM {sales}
GROUP BY CATEGORY
ORDER BY {alias} DESC
""".strip()

    if _question_unsupported(user_question):
        return INSUFFICIENT

    # Monthly sales growth (Phase 11 default analytic)
    if "growth" in q and ("monthly" in q or "month" in q) and (
        "sales" in q or "revenue" in q
    ):
        return f"""
SELECT
  ORDER_MONTH,
  SUM(SALES) AS REVENUE,
  LAG(SUM(SALES)) OVER (ORDER BY ORDER_MONTH) AS PRIOR_REVENUE,
  (SUM(SALES) - LAG(SUM(SALES)) OVER (ORDER BY ORDER_MONTH))
    / NULLIF(LAG(SUM(SALES)) OVER (ORDER BY ORDER_MONTH), 0) AS MOM_GROWTH
FROM {sales}
GROUP BY ORDER_MONTH
ORDER BY ORDER_MONTH
""".strip()

    if re.search(r"average order value|\baov\b", q):
        return f"""
SELECT
  SUM(SALES) / NULLIF(COUNT(DISTINCT ORDER_ID), 0) AS AVERAGE_ORDER_VALUE
FROM {sales}
""".strip()

    if "profit margin" in q and "region" in q:
        return f"""
SELECT REGION,
       SUM(PROFIT) / NULLIF(SUM(SALES), 0) AS PROFIT_MARGIN
FROM {sales}
GROUP BY REGION
ORDER BY PROFIT_MARGIN DESC
""".strip()

    if "profit margin" in q and "categor" in q:
        return f"""
SELECT CATEGORY,
       SUM(PROFIT) / NULLIF(SUM(SALES), 0) AS PROFIT_MARGIN
FROM {sales}
GROUP BY CATEGORY
ORDER BY PROFIT_MARGIN DESC
""".strip()

    if re.search(r"total revenue|what is (our )?total (revenue|sales)|total sales\b", q):
        return f"SELECT SUM(SALES) AS TOTAL_REVENUE FROM {sales}"

    if re.search(r"total profit|what is (our )?total profit", q):
        return f"SELECT SUM(PROFIT) AS TOTAL_PROFIT FROM {sales}"

    if "negative profit" in q or "worst-performing" in q or "worst performing" in q:
        return f"""
SELECT PRODUCT_ID, PRODUCT_NAME, TOTAL_SALES, TOTAL_PROFIT
FROM {products}
WHERE TOTAL_PROFIT < 0
ORDER BY TOTAL_PROFIT ASC
LIMIT 50
""".strip()

    if "top" in q and "customer" in q:
        return f"""
SELECT CUSTOMER_ID, CUSTOMER_NAME, TOTAL_SALES, TOTAL_PROFIT
FROM {customers}
ORDER BY TOTAL_SALES DESC
LIMIT 10
""".strip()

    if ("top" in q or "highest" in q) and "product" in q and "profit" in q:
        return f"""
SELECT PRODUCT_ID, PRODUCT_NAME, TOTAL_PROFIT, TOTAL_SALES
FROM {products}
ORDER BY TOTAL_PROFIT DESC
LIMIT 10
""".strip()

    if ("top" in q or "highest" in q) and "product" in q and "quantity" in q:
        return f"""
SELECT PRODUCT_ID, PRODUCT_NAME, TOTAL_QUANTITY, TOTAL_SALES
FROM {products}
ORDER BY TOTAL_QUANTITY DESC
LIMIT 10
""".strip()

    if ("top" in q or "highest" in q) and "product" in q:
        return f"""
SELECT PRODUCT_ID, PRODUCT_NAME, TOTAL_SALES, TOTAL_PROFIT
FROM {products}
ORDER BY TOTAL_SALES DESC
LIMIT 10
""".strip()

    if "monthly" in q and ("revenue" in q or "sales" in q):
        return f"""
SELECT ORDER_MONTH, SUM(SALES) AS REVENUE
FROM {sales}
GROUP BY ORDER_MONTH
ORDER BY ORDER_MONTH
""".strip()

    if "monthly" in q and "profit" in q:
        return f"""
SELECT ORDER_MONTH, SUM(PROFIT) AS PROFIT
FROM {sales}
GROUP BY ORDER_MONTH
ORDER BY ORDER_MONTH
""".strip()

    if "sales trend" in q or "revenue trend" in q:
        return f"""
SELECT ORDER_MONTH, SUM(SALES) AS REVENUE
FROM {sales}
GROUP BY ORDER_MONTH
ORDER BY ORDER_MONTH
""".strip()

    if "by year" in q or ("compare" in q and "year" in q):
        metric = "PROFIT" if "profit" in q else "SALES"
        alias = "TOTAL_PROFIT" if metric == "PROFIT" else "TOTAL_REVENUE"
        return f"""
SELECT ORDER_YEAR, SUM({metric}) AS {alias}
FROM {sales}
GROUP BY ORDER_YEAR
ORDER BY ORDER_YEAR
""".strip()

    if "by region" in q or "revenue by region" in q or "sales by region" in q:
        metric = "PROFIT" if "profit" in q and "sales" not in q and "revenue" not in q else "SALES"
        alias = "TOTAL_PROFIT" if metric == "PROFIT" else "TOTAL_REVENUE"
        return f"""
SELECT REGION, SUM({metric}) AS {alias}
FROM {sales}
GROUP BY REGION
ORDER BY {alias} DESC
""".strip()

    if "by segment" in q or "customer segment" in q:
        return f"""
SELECT SEGMENT, SUM(SALES) AS TOTAL_REVENUE
FROM {sales}
GROUP BY SEGMENT
ORDER BY TOTAL_REVENUE DESC
""".strip()

    if "by categor" in q or "contribution by categor" in q or "percentage" in q and "categor" in q:
        return f"""
SELECT CATEGORY,
       SUM(SALES) AS TOTAL_REVENUE,
       SUM(SALES) / NULLIF(SUM(SUM(SALES)) OVER (), 0) AS PCT_OF_SALES
FROM {sales}
GROUP BY CATEGORY
ORDER BY TOTAL_REVENUE DESC
""".strip()

    if "sub-categor" in q or "sub_categor" in q or "subcategor" in q:
        return f"""
SELECT SUB_CATEGORY, SUM(SALES) AS TOTAL_REVENUE
FROM {sales}
GROUP BY SUB_CATEGORY
ORDER BY TOTAL_REVENUE DESC
LIMIT 50
""".strip()

    if "state" in q and ("highest" in q or "top" in q or "by state" in q):
        return f"""
SELECT STATE, SUM(SALES) AS TOTAL_REVENUE
FROM {sales}
GROUP BY STATE
ORDER BY TOTAL_REVENUE DESC
LIMIT 20
""".strip()

    if "categor" in q and ("highest" in q or "top" in q) and "profit" in q:
        return f"""
SELECT CATEGORY, SUM(PROFIT) AS TOTAL_PROFIT
FROM {sales}
GROUP BY CATEGORY
ORDER BY TOTAL_PROFIT DESC
""".strip()

    if "categor" in q and ("highest" in q or "top" in q):
        return f"""
SELECT CATEGORY, SUM(SALES) AS TOTAL_REVENUE
FROM {sales}
GROUP BY CATEGORY
ORDER BY TOTAL_REVENUE DESC
""".strip()

    if "sales vs profit" in q or ("sales" in q and "profit" in q and "categor" in q):
        return f"""
SELECT CATEGORY, SUM(SALES) AS TOTAL_REVENUE, SUM(PROFIT) AS TOTAL_PROFIT
FROM {sales}
GROUP BY CATEGORY
ORDER BY TOTAL_REVENUE DESC
""".strip()

    if "high sales" in q and "low profit" in q:
        return f"""
SELECT PRODUCT_ID, PRODUCT_NAME, TOTAL_SALES, TOTAL_PROFIT, PROFIT_MARGIN
FROM {products}
WHERE TOTAL_SALES > 0
ORDER BY TOTAL_SALES DESC, TOTAL_PROFIT ASC
LIMIT 20
""".strip()

    # Default: do not hallucinate — ask for clearer question via insufficient
    return INSUFFICIENT


def generate_sql(
    user_question: str,
    conversation_context: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
    *,
    provider: str | None = None,
    allow_heuristic_fallback: bool = True,
) -> str:
    """
    Convert a natural-language question into Snowflake SELECT SQL.

    Returns SQL text, or the literal string INSUFFICIENT_DATA.
    """
    result = generate_sql_detailed(
        user_question,
        conversation_context,
        metadata,
        provider=provider,
        allow_heuristic_fallback=allow_heuristic_fallback,
    )
    return result.sql


def generate_sql_detailed(
    user_question: str,
    conversation_context: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
    *,
    provider: str | None = None,
    allow_heuristic_fallback: bool = True,
) -> SqlGenerationResult:
    import time

    started = time.perf_counter()
    provider = (provider or _provider_name()).strip().lower()

    if not (user_question or "").strip():
        return SqlGenerationResult(
            sql=INSUFFICIENT,
            status="insufficient_data",
            provider=provider,
            error="Empty question",
        )

    if _question_unsupported(user_question):
        return SqlGenerationResult(
            sql=INSUFFICIENT,
            status="insufficient_data",
            provider="policy",
            latency_ms=(time.perf_counter() - started) * 1000,
            error="Question topics are outside the available dataset",
        )

    schema_text, glossary, relationships = _format_metadata_block(metadata)
    full_prompt = build_full_sql_prompt(
        user_question, schema_text, glossary, relationships, conversation_context
    )
    user_prompt = build_sql_user_prompt(
        user_question, schema_text, glossary, relationships, conversation_context
    )

    raw = ""
    used = provider
    err: str | None = None

    try:
        if provider in {"snowflake_cortex", "cortex"}:
            raw = _call_cortex(full_prompt)
            used = "snowflake_cortex"
        elif provider == "openai":
            raw = _call_openai(user_prompt)
            used = "openai"
        elif provider in {"heuristic", "rules", "offline"}:
            sql = heuristic_sql(user_question, conversation_context)
            return SqlGenerationResult(
                sql=sql,
                status="ok" if sql != INSUFFICIENT else "insufficient_data",
                provider="heuristic",
                latency_ms=(time.perf_counter() - started) * 1000,
                raw_response=sql,
            )
        else:
            # auto: try cortex then openai then heuristic
            used = "auto"
            try:
                raw = _call_cortex(full_prompt)
                used = "snowflake_cortex"
            except Exception as cortex_exc:
                err = f"cortex: {cortex_exc}"
                if os.getenv("OPENAI_API_KEY"):
                    raw = _call_openai(user_prompt)
                    used = "openai"
                elif allow_heuristic_fallback:
                    sql = heuristic_sql(user_question, conversation_context)
                    return SqlGenerationResult(
                        sql=sql,
                        status="ok" if sql != INSUFFICIENT else "insufficient_data",
                        provider="heuristic",
                        latency_ms=(time.perf_counter() - started) * 1000,
                        raw_response=sql,
                        error=err,
                        warnings=["Fell back to heuristic SQL generator"],
                    )
                else:
                    raise
    except Exception as exc:
        if allow_heuristic_fallback and provider not in {"heuristic", "rules", "offline"}:
            sql = heuristic_sql(user_question, conversation_context)
            return SqlGenerationResult(
                sql=sql,
                status="ok" if sql != INSUFFICIENT else "insufficient_data",
                provider="heuristic",
                latency_ms=(time.perf_counter() - started) * 1000,
                raw_response=sql,
                error=str(exc),
                warnings=["LLM failed; used heuristic SQL generator"],
            )
        return SqlGenerationResult(
            sql=INSUFFICIENT,
            status="error",
            provider=used,
            latency_ms=(time.perf_counter() - started) * 1000,
            error=str(exc),
        )

    sql = _normalize_llm_sql(raw)
    if not sql:
        if allow_heuristic_fallback:
            sql = heuristic_sql(user_question, conversation_context)
            used = "heuristic"
        else:
            sql = INSUFFICIENT

    status = "insufficient_data" if sql == INSUFFICIENT else "ok"
    return SqlGenerationResult(
        sql=sql,
        status=status,
        provider=used,
        latency_ms=(time.perf_counter() - started) * 1000,
        raw_response=raw,
        error=err,
    )
