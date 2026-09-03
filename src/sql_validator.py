"""
SQL safety validation (Phase 6).

Ensures only read-only SELECT/WITH queries reach Snowflake.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Destructive / mutating statement keywords (word-boundary match)
FORBIDDEN_KEYWORDS = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "MERGE",
    "GRANT",
    "REVOKE",
    "CALL",
    "EXECUTE",
    "COPY",
    "PUT",
    "GET",
    "REMOVE",
    "UNDROP",
    "USE",  # prevent switching role/warehouse mid-query scripts
    "BEGIN",
    "COMMIT",
    "ROLLBACK",
]

# Aggregation / already-limited patterns — skip auto LIMIT
_HAS_LIMIT = re.compile(r"\bLIMIT\s+\d+", re.IGNORECASE)
_HAS_GROUP_BY = re.compile(r"\bGROUP\s+BY\b", re.IGNORECASE)
_HAS_AGG = re.compile(
    r"\b(SUM|COUNT|AVG|MIN|MAX|APPROX_COUNT_DISTINCT)\s*\(",
    re.IGNORECASE,
)
_DEFAULT_DETAIL_LIMIT = 100


@dataclass
class ValidationResult:
    ok: bool
    sql: str
    error: str = ""
    warnings: list[str] = field(default_factory=list)
    rejected_reason: str | None = None


def _strip_markdown_fences(sql: str) -> str:
    text = (sql or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:sql)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _strip_sql_comments(sql: str) -> str:
    """Remove -- and /* */ comments to avoid keyword smuggling in comments."""
    no_block = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    no_line = re.sub(r"--.*?$", " ", no_block, flags=re.MULTILINE)
    return no_line


def _split_statements(sql: str) -> list[str]:
    """Split on semicolons outside single-quoted strings (simple MVP parser)."""
    parts: list[str] = []
    buf: list[str] = []
    in_single = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        if ch == "'" and not in_single:
            in_single = True
            buf.append(ch)
        elif ch == "'" and in_single:
            # handle escaped '' inside strings
            if i + 1 < len(sql) and sql[i + 1] == "'":
                buf.append("''")
                i += 2
                continue
            in_single = False
            buf.append(ch)
        elif ch == ";" and not in_single:
            stmt = "".join(buf).strip()
            if stmt:
                parts.append(stmt)
            buf = []
        else:
            buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts


def _find_forbidden(sql_no_comments: str) -> str | None:
    """Scan for forbidden keywords outside of single-quoted string literals."""
    # Mask string literals so keywords inside quotes do not trigger rejection
    masked = re.sub(r"'(?:''|[^'])*'", "''", sql_no_comments)
    upper = masked.upper()
    for kw in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{kw}\b", upper):
            return kw
    return None


def _starts_with_select_or_with(sql: str) -> bool:
    cleaned = sql.lstrip().lstrip("(").lstrip()
    return bool(re.match(r"(?is)^(WITH|SELECT)\b", cleaned))


def _maybe_add_limit(sql: str, limit: int = _DEFAULT_DETAIL_LIMIT) -> tuple[str, bool]:
    """Add LIMIT for uncontrolled detail queries (no GROUP BY / agg / existing LIMIT)."""
    if _HAS_LIMIT.search(sql):
        return sql, False
    if _HAS_GROUP_BY.search(sql) or _HAS_AGG.search(sql):
        return sql, False
    # Likely a detail listing — enforce a safety limit
    return f"{sql.rstrip().rstrip(';')}\nLIMIT {limit}", True


def validate_sql(
    sql: str,
    *,
    add_limit: bool = True,
    detail_limit: int = _DEFAULT_DETAIL_LIMIT,
    log_rejections: bool = True,
) -> tuple[bool, str, str]:
    """
    Validate that SQL is a safe read-only Snowflake query.

    Returns:
        (ok, sanitized_sql_or_empty, error_message)
    """
    result = validate_sql_detailed(
        sql,
        add_limit=add_limit,
        detail_limit=detail_limit,
        log_rejections=log_rejections,
    )
    return result.ok, result.sql if result.ok else "", result.error


def validate_sql_detailed(
    sql: str,
    *,
    add_limit: bool = True,
    detail_limit: int = _DEFAULT_DETAIL_LIMIT,
    log_rejections: bool = True,
) -> ValidationResult:
    warnings: list[str] = []

    if sql is None or not str(sql).strip():
        return ValidationResult(False, "", "SQL is empty.")

    text = _strip_markdown_fences(str(sql))
    if text.upper().strip() == "INSUFFICIENT_DATA":
        return ValidationResult(
            False,
            "",
            "No executable SQL (INSUFFICIENT_DATA).",
            rejected_reason="insufficient_data",
        )

    # Disallow multiple statements
    statements = _split_statements(text)
    if len(statements) > 1:
        msg = "Multiple SQL statements are not allowed."
        _log_reject(text, msg, log_rejections)
        return ValidationResult(False, "", msg, rejected_reason="multiple_statements")

    statement = statements[0] if statements else text
    no_comments = _strip_sql_comments(statement)

    forbidden = _find_forbidden(no_comments)
    if forbidden:
        msg = (
            f"Rejected unsafe SQL: '{forbidden}' statements are not allowed. "
            "Only read-only SELECT queries may run."
        )
        _log_reject(statement, msg, log_rejections)
        return ValidationResult(False, "", msg, rejected_reason=forbidden)

    if not _starts_with_select_or_with(no_comments):
        msg = "Only SELECT or WITH (CTE) queries are allowed."
        _log_reject(statement, msg, log_rejections)
        return ValidationResult(False, "", msg, rejected_reason="not_select")

    # Block SELECT ... INTO / SELECT INTO variants
    if re.search(r"\bINTO\b", no_comments, re.IGNORECASE):
        msg = "SELECT INTO is not allowed."
        _log_reject(statement, msg, log_rejections)
        return ValidationResult(False, "", msg, rejected_reason="select_into")

    sanitized = statement.rstrip().rstrip(";")
    if add_limit:
        sanitized, limited = _maybe_add_limit(sanitized, detail_limit)
        if limited:
            warnings.append(f"Added LIMIT {detail_limit} for safety on a detail query.")

    return ValidationResult(True, sanitized, "", warnings=warnings)


def _log_reject(sql: str, reason: str, enabled: bool) -> None:
    if not enabled:
        return
    preview = re.sub(r"\s+", " ", sql)[:500]
    logger.warning("Rejected SQL (%s): %s", reason, preview)
