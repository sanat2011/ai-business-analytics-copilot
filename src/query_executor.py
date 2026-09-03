"""
Execute validated read-only SQL against Snowflake (Phase 7).

Flow: validate → execute → pandas DataFrame → structured result.
Optionally writes a row to ANALYTICS_AI_DB.AI.QUERY_LOG when available.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from src.sql_validator import validate_sql_detailed

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    ok: bool
    sql: str = ""
    dataframe: pd.DataFrame | None = None
    row_count: int = 0
    execution_time_ms: float = 0.0
    validation_time_ms: float = 0.0
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    empty: bool = False

    def summary(self, max_rows: int = 5) -> str:
        if not self.ok:
            return self.error or "Query failed"
        if self.dataframe is None or self.dataframe.empty:
            return "Empty result set"
        head = self.dataframe.head(max_rows)
        return f"{self.row_count} rows; preview:\n{head.to_string(index=False)}"


def execute_query(
    sql: str,
    *,
    user_question: str | None = None,
    skip_validation: bool = False,
    log_to_snowflake: bool = True,
    session: Any | None = None,
    visualization_type: str | None = None,
) -> QueryResult:
    """
    Validate (unless skipped) and execute a read-only SQL query.

    Returns a QueryResult with dataframe on success.
    """
    warnings: list[str] = []
    t0 = time.perf_counter()

    if skip_validation:
        safe_sql = (sql or "").strip().rstrip(";")
        validation_ms = 0.0
        if not safe_sql:
            return QueryResult(ok=False, error="SQL is empty.")
    else:
        validation = validate_sql_detailed(sql)
        validation_ms = (time.perf_counter() - t0) * 1000
        warnings.extend(validation.warnings)
        if not validation.ok:
            result = QueryResult(
                ok=False,
                sql=sql or "",
                validation_time_ms=validation_ms,
                error=validation.error or "SQL validation failed",
                warnings=warnings,
            )
            _maybe_log(
                user_question=user_question,
                sql=sql or "",
                status="validation_failed",
                execution_time_ms=0,
                row_count=0,
                error=result.error,
                log_to_snowflake=log_to_snowflake,
                session=session,
                visualization_type=visualization_type,
            )
            return result
        safe_sql = validation.sql

    t1 = time.perf_counter()
    try:
        df = _run_sql(safe_sql, session=session)
        exec_ms = (time.perf_counter() - t1) * 1000
        row_count = int(len(df))
        empty = row_count == 0
        result = QueryResult(
            ok=True,
            sql=safe_sql,
            dataframe=df,
            row_count=row_count,
            execution_time_ms=exec_ms,
            validation_time_ms=validation_ms,
            warnings=warnings,
            empty=empty,
            error="Query returned no rows." if empty else None,
        )
        _maybe_log(
            user_question=user_question,
            sql=safe_sql,
            status="empty" if empty else "success",
            execution_time_ms=exec_ms,
            row_count=row_count,
            error=result.error,
            log_to_snowflake=log_to_snowflake,
            session=session,
            visualization_type=visualization_type,
        )
        return result
    except Exception as exc:
        exec_ms = (time.perf_counter() - t1) * 1000
        msg = _friendly_error(exc)
        logger.exception("Snowflake query failed")
        result = QueryResult(
            ok=False,
            sql=safe_sql,
            execution_time_ms=exec_ms,
            validation_time_ms=validation_ms,
            error=msg,
            warnings=warnings,
        )
        _maybe_log(
            user_question=user_question,
            sql=safe_sql,
            status="execution_failed",
            execution_time_ms=exec_ms,
            row_count=0,
            error=msg,
            log_to_snowflake=log_to_snowflake,
            session=session,
            visualization_type=visualization_type,
        )
        return result


def _run_sql(sql: str, session: Any | None = None) -> pd.DataFrame:
    if session is None:
        from src.snowflake_connection import get_session

        session = get_session()
    return session.sql(sql).to_pandas()


def _friendly_error(exc: Exception) -> str:
    text = str(exc)
    lower = text.lower()
    if "timeout" in lower or "timed out" in lower:
        return "Snowflake query timed out. Try a narrower question or a smaller warehouse."
    if "incorrect username or password" in lower:
        return "Snowflake authentication failed. Check credentials or use Streamlit-in-Snowflake."
    if "does not exist" in lower or "object does not exist" in lower:
        return f"Snowflake object missing or not granted: {text}"
    if "permission" in lower or "access control" in lower or "insufficient privileges" in lower:
        return f"Insufficient Snowflake privileges to run this query: {text}"
    return f"Snowflake execution failed: {text}"


def log_query_event(
    *,
    user_question: str | None,
    sql: str,
    status: str,
    execution_time_ms: float,
    row_count: int,
    error: str | None = None,
    visualization_type: str | None = None,
    session: Any | None = None,
) -> None:
    """Public helper for AI query observability logging."""
    _maybe_log(
        user_question=user_question,
        sql=sql,
        status=status,
        execution_time_ms=execution_time_ms,
        row_count=row_count,
        error=error,
        log_to_snowflake=True,
        session=session,
        visualization_type=visualization_type,
    )


def _maybe_log(
    *,
    user_question: str | None,
    sql: str,
    status: str,
    execution_time_ms: float,
    row_count: int,
    error: str | None,
    log_to_snowflake: bool,
    session: Any | None,
    visualization_type: str | None = None,
) -> None:
    if not log_to_snowflake:
        return
    try:
        if session is None:
            from src.snowflake_connection import get_session

            session = get_session()
        q = (user_question or "").replace("'", "''")[:4000]
        s = (sql or "").replace("'", "''")[:8000]
        e = (error or "").replace("'", "''")[:4000]
        viz = (visualization_type or "").replace("'", "''")[:100]
        viz_sql = "NULL" if not viz else f"'{viz}'"
        err_sql = "NULL" if not e else f"'{e}'"
        session.sql(
            f"""
            INSERT INTO ANALYTICS_AI_DB.AI.QUERY_LOG
              (USER_QUESTION, GENERATED_SQL, EXECUTION_STATUS, EXECUTION_TIME_MS,
               ROW_COUNT, ERROR_MESSAGE, VISUALIZATION_TYPE)
            VALUES
              ('{q}', '{s}', '{status}', {int(execution_time_ms)}, {int(row_count)},
               {err_sql}, {viz_sql})
            """
        ).collect()
    except Exception as log_exc:
        logger.debug("QUERY_LOG write skipped: %s", log_exc)