"""
Business insight generation (Phase 10).

Rules:
  - Use only values present in the result
  - Do not invent facts or unsupported predictions
  - Keep to 2–4 sentences
  - Prefer Cortex / OpenAI when configured; heuristic fallback otherwise
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.prompts import INSIGHT_SYSTEM_PROMPT

MAX_PREVIEW_ROWS = 15
MAX_PREVIEW_COLS = 8


@dataclass
class InsightResult:
    text: str
    provider: str
    latency_ms: float = 0.0
    error: str | None = None


def _dataframe_preview(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "(empty)"
    slim = df.iloc[:MAX_PREVIEW_ROWS, :MAX_PREVIEW_COLS].copy()
    # Round floats for compact, stable text
    for col in slim.select_dtypes(include="number").columns:
        slim[col] = slim[col].map(lambda v: None if pd.isna(v) else round(float(v), 2))
    return slim.to_string(index=False)


def _provider_name() -> str:
    return (os.getenv("LLM_PROVIDER") or "heuristic").strip().lower()


def _call_cortex(prompt: str) -> str:
    from src.snowflake_connection import get_session

    model = os.getenv("CORTEX_MODEL") or "mistral-large"
    session = get_session()
    rows = session.sql(
        "SELECT SNOWFLAKE.CORTEX.COMPLETE(?, ?) AS RESP",
        params=(model, prompt),
    ).collect()
    return rows[0]["RESP"] if rows else ""


def _call_openai(prompt: str) -> str:
    import json
    import urllib.request

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    body = {
        "model": os.getenv("OPENAI_MODEL") or "gpt-4o-mini",
        "temperature": 0,
        "messages": [
            {"role": "system", "content": INSIGHT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
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


def _build_prompt(question: str, preview: str) -> str:
    return f"""{INSIGHT_SYSTEM_PROMPT}

User question:
{question}

Query result (use ONLY these values; do not invent numbers):
{preview}

Write a short business insight (2–4 sentences).
"""


def heuristic_insight(question: str, df: pd.DataFrame | None) -> str:
    """Deterministic insight from result values only (no LLM)."""
    if df is None or df.empty:
        return "There is insufficient information in the result to form a business insight."

    q = (question or "").lower()
    nums = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    cats = [c for c in df.columns if c not in nums]

    # Single KPI
    if df.shape[0] == 1 and len(nums) >= 1:
        col = nums[0]
        val = df.iloc[0][col]
        label = str(col).replace("_", " ").title()
        try:
            return (
                f"The result for “{question}” is {label} = {float(val):,.2f}. "
                f"This figure is taken directly from the query output."
            )
        except Exception:
            return f"The result for “{question}” is {label} = {val}."

    if not nums:
        return (
            f"The query returned {len(df)} row(s) related to “{question}”. "
            "No numeric metrics were present to compare."
        )

    metric = nums[0]
    label_col = cats[0] if cats else None
    work = df.dropna(subset=[metric]).copy()
    if work.empty:
        return "There is insufficient numeric information in the result to form an insight."

    work = work.sort_values(metric, ascending=False)
    top = work.iloc[0]
    top_val = float(top[metric])
    total = float(work[metric].sum()) if work[metric].sum() else None

    if label_col:
        top_name = str(top[label_col])
        if len(work) >= 2:
            second = work.iloc[1]
            second_name = str(second[label_col])
            second_val = float(second[metric])
            if second_val != 0:
                pct_ahead = ((top_val - second_val) / abs(second_val)) * 100
                lead = (
                    f"{top_name} led with {top_val:,.2f} on {metric.replace('_', ' ').lower()}, "
                    f"about {pct_ahead:.1f}% ahead of {second_name} ({second_val:,.2f}). "
                )
            else:
                lead = (
                    f"{top_name} led with {top_val:,.2f} on {metric.replace('_', ' ').lower()}, "
                    f"ahead of {second_name}. "
                )
        else:
            lead = f"{top_name} recorded {top_val:,.2f} on {metric.replace('_', ' ').lower()}. "

        share = ""
        if total and total != 0 and len(work) >= 2:
            share = f"{top_name} represents {top_val / total * 100:.1f}% of the listed total ({total:,.2f}). "

        trend = ""
        if any(w in q for w in ("trend", "monthly", "over time", "growth")):
            bottom = work.iloc[-1]
            trend = (
                f"Across the returned series, values range from "
                f"{float(work[metric].min()):,.2f} to {float(work[metric].max()):,.2f}."
            )
            _ = bottom  # values already covered by min/max
            return (lead + share + trend).strip()

        negative = work[work[metric] < 0]
        neg_note = ""
        if not negative.empty and "profit" in metric.lower():
            neg_note = f"{len(negative)} item(s) show negative {metric.replace('_', ' ').lower()}. "

        return (lead + share + neg_note).strip()

    return (
        f"The highest {metric.replace('_', ' ').lower()} in the result is {top_val:,.2f}. "
        f"The query returned {len(work)} numeric row(s) for “{question}”."
    )


def generate_insight(
    question: str,
    result_dataframe: pd.DataFrame | None,
    *,
    provider: str | None = None,
    allow_heuristic_fallback: bool = True,
) -> str:
    return generate_insight_detailed(
        question,
        result_dataframe,
        provider=provider,
        allow_heuristic_fallback=allow_heuristic_fallback,
    ).text


def generate_insight_detailed(
    question: str,
    result_dataframe: pd.DataFrame | None,
    *,
    provider: str | None = None,
    allow_heuristic_fallback: bool = True,
) -> InsightResult:
    import time

    started = time.perf_counter()
    provider = (provider or _provider_name()).strip().lower()

    if result_dataframe is None or result_dataframe.empty:
        return InsightResult(
            text="There is insufficient information in the result to form a business insight.",
            provider="policy",
            latency_ms=(time.perf_counter() - started) * 1000,
        )

    preview = _dataframe_preview(result_dataframe)
    prompt = _build_prompt(question, preview)

    try:
        if provider in {"snowflake_cortex", "cortex"}:
            raw = _call_cortex(prompt)
            used = "snowflake_cortex"
        elif provider == "openai":
            raw = _call_openai(prompt)
            used = "openai"
        elif provider in {"heuristic", "rules", "offline"}:
            text = heuristic_insight(question, result_dataframe)
            return InsightResult(
                text=text,
                provider="heuristic",
                latency_ms=(time.perf_counter() - started) * 1000,
            )
        else:  # auto
            try:
                raw = _call_cortex(prompt)
                used = "snowflake_cortex"
            except Exception:
                if os.getenv("OPENAI_API_KEY"):
                    raw = _call_openai(prompt)
                    used = "openai"
                elif allow_heuristic_fallback:
                    text = heuristic_insight(question, result_dataframe)
                    return InsightResult(
                        text=text,
                        provider="heuristic",
                        latency_ms=(time.perf_counter() - started) * 1000,
                        error="LLM unavailable; used heuristic insight",
                    )
                else:
                    raise
    except Exception as exc:
        if allow_heuristic_fallback:
            text = heuristic_insight(question, result_dataframe)
            return InsightResult(
                text=text,
                provider="heuristic",
                latency_ms=(time.perf_counter() - started) * 1000,
                error=str(exc),
            )
        return InsightResult(
            text="Insight generation failed.",
            provider=provider,
            latency_ms=(time.perf_counter() - started) * 1000,
            error=str(exc),
        )

    text = (raw or "").strip()
    # Strip accidental markdown fences
    text = re.sub(r"^```(?:\w+)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text).strip()
    if not text and allow_heuristic_fallback:
        text = heuristic_insight(question, result_dataframe)
        used = "heuristic"

    # Keep insights concise
    sentences = re.split(r"(?<=[.!?])\s+", text)
    if len(sentences) > 4:
        text = " ".join(sentences[:4]).strip()

    return InsightResult(
        text=text,
        provider=used,
        latency_ms=(time.perf_counter() - started) * 1000,
    )
