"""SQL safety validation (Phase 6)."""

from __future__ import annotations


def validate_sql(sql: str) -> tuple[bool, str, str]:
    """
    Returns (ok, sanitized_sql_or_empty, error_message).
    """
    raise NotImplementedError("Phase 6 — validate_sql()")
