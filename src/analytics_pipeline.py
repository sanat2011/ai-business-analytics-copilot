"""
End-to-end analytics turn: question → SQL → validate → execute.

Used by the Streamlit chat UI (Phase 8). Visualization/insights added later.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import pandas as pd

from src.insight_generator import generate_insight_detailed
from src.query_executor import execute_query
from src.sql_generator import generate_sql_detailed


@dataclass
class AnalyticsTurn:
    question: str
    ok: bool
    message: str
    sql: str = ""
    provider: str = ""
    generation_ms: float = 0.0
    execution_ms: float = 0.0
    insight_ms: float = 0.0
    row_count: int = 0
    dataframe: pd.DataFrame | None = None
    result_summary: str = ""
    insight: str = ""
    insight_provider: str = ""
    warnings: list[str] = field(default_factory=list)
    error: str | None = None
    status: str = ""  # insufficient_data | validation_failed | execution_failed | success | empty

    def context_blob(self) -> dict[str, Any]:
        """Compact context for follow-up SQL generation (no full dataframe)."""
        return {
            "question": self.question,
            "user_question": self.question,
            "sql": self.sql,
            "generated_sql": self.sql,
            "result_summary": self.result_summary,
            "insight": self.insight,
        }


def run_analytics_question(
    question: str,
    *,
    conversation_context: list[dict[str, Any]] | None = None,
    provider: str = "heuristic",
    log_to_snowflake: bool = True,
) -> AnalyticsTurn:
    question = (question or "").strip()
    if not question:
        return AnalyticsTurn(
            question="",
            ok=False,
            message="Please enter a business question.",
            status="error",
            error="Empty question",
        )

    gen = generate_sql_detailed(
        question,
        conversation_context=conversation_context,
        provider=provider,
    )
    if gen.status == "insufficient_data":
        return AnalyticsTurn(
            question=question,
            ok=False,
            message=(
                "I cannot answer this question because the required data "
                "is not available in the current Snowflake dataset."
            ),
            provider=gen.provider,
            generation_ms=gen.latency_ms,
            status="insufficient_data",
            error=gen.error,
            warnings=list(gen.warnings),
        )
    if gen.status != "ok":
        return AnalyticsTurn(
            question=question,
            ok=False,
            message=gen.error or "SQL generation failed.",
            provider=gen.provider,
            generation_ms=gen.latency_ms,
            status="error",
            error=gen.error,
            warnings=list(gen.warnings),
        )

    qres = execute_query(
        gen.sql,
        user_question=question,
        log_to_snowflake=False,  # pipeline logs once with visualization_type
    )
    warnings = list(gen.warnings) + list(qres.warnings)

    if not qres.ok:
        # Distinguish validation vs execution from error text
        status = (
            "validation_failed"
            if "not allowed" in (qres.error or "").lower()
            or "validation" in (qres.error or "").lower()
            or "insufficient_data" in (qres.error or "").lower()
            else "execution_failed"
        )
        return AnalyticsTurn(
            question=question,
            ok=False,
            message=qres.error or "Query failed.",
            sql=qres.sql or gen.sql,
            provider=gen.provider,
            generation_ms=gen.latency_ms,
            execution_ms=qres.execution_time_ms,
            status=status,
            error=qres.error,
            warnings=warnings,
        )

    if qres.empty:
        return AnalyticsTurn(
            question=question,
            ok=True,
            message="The query ran successfully but returned no rows.",
            sql=qres.sql,
            provider=gen.provider,
            generation_ms=gen.latency_ms,
            execution_ms=qres.execution_time_ms,
            row_count=0,
            dataframe=qres.dataframe,
            result_summary="empty result",
            insight="There is insufficient information in the result to form a business insight.",
            insight_provider="policy",
            status="empty",
            warnings=warnings,
        )

    summary = qres.summary(max_rows=5)
    insight = generate_insight_detailed(
        question,
        qres.dataframe,
        provider=provider,
    )
    if insight.error:
        warnings.append(insight.error)

    from src.visualization import choose_visualization

    viz = choose_visualization(qres.dataframe, question) if qres.dataframe is not None else None

    # Full observability row (includes visualization type)
    if log_to_snowflake:
        from src.query_executor import log_query_event

        log_query_event(
            user_question=question,
            sql=qres.sql,
            status="success",
            execution_time_ms=qres.execution_time_ms,
            row_count=qres.row_count,
            error=None,
            visualization_type=viz,
        )

    return AnalyticsTurn(
        question=question,
        ok=True,
        message=f"Returned {qres.row_count} row(s).",
        sql=qres.sql,
        provider=gen.provider,
        generation_ms=gen.latency_ms,
        execution_ms=qres.execution_time_ms,
        insight_ms=insight.latency_ms,
        row_count=qres.row_count,
        dataframe=qres.dataframe,
        result_summary=summary,
        insight=insight.text,
        insight_provider=insight.provider,
        status="success",
        warnings=warnings,
    )


def turn_to_history_entry(turn: AnalyticsTurn) -> dict[str, Any]:
    """Session-state friendly dict (dataframe kept separately for display)."""
    payload = asdict(turn)
    # DataFrames are not JSON-serializable; keep reference in session list as object
    return payload
