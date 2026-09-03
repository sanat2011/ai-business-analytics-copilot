"""
Conversation context helpers (Phase 12).

Keeps compact prior-turn context for follow-ups like "their profit".
"""

from __future__ import annotations

import re
from typing import Any


def build_conversation_context(messages: list[dict[str, Any]], limit: int = 4) -> list[dict[str, Any]]:
    """Extract compact context blobs from Streamlit chat message history."""
    ctx: list[dict[str, Any]] = []
    for msg in messages:
        if msg.get("role") != "assistant":
            continue
        turn = msg.get("turn") or {}
        if not turn.get("sql"):
            continue
        entity = infer_entity_from_question(turn.get("question") or "")
        ctx.append(
            {
                "question": turn.get("question"),
                "user_question": turn.get("question"),
                "sql": turn.get("sql"),
                "generated_sql": turn.get("sql"),
                "result_summary": (turn.get("result_summary") or "")[:500],
                "insight": (turn.get("insight") or "")[:300],
                "entity": entity,
                "row_count": turn.get("row_count"),
            }
        )
    return ctx[-limit:]


def infer_entity_from_question(question: str) -> str:
    q = (question or "").lower()
    if "customer" in q:
        return "customers"
    if "product" in q:
        return "products"
    if "region" in q:
        return "regions"
    if "segment" in q:
        return "segments"
    if "categor" in q:
        return "categories"
    if "state" in q:
        return "states"
    return "unknown"


def is_follow_up(question: str) -> bool:
    q = (question or "").strip().lower()
    if re.search(r"\b(their|those|these|same|previous|them)\b", q):
        return True
    if re.match(r"^(now |and |also |what about |how about )", q):
        return True
    if re.match(r"^(show|give|list)\s+(me\s+)?(the\s+)?(profit|sales|revenue|margin)", q):
        # Ambiguous short asks often follow a ranked list
        return True
    return False


def resolve_follow_up_entity(
    question: str, conversation_context: list[dict[str, Any]] | None
) -> str | None:
    if not conversation_context:
        return None
    if not is_follow_up(question):
        return None
    prev = conversation_context[-1]
    return prev.get("entity") or infer_entity_from_question(
        prev.get("question") or prev.get("user_question") or ""
    )
