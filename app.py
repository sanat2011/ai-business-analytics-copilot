"""
AI Business Analytics Copilot — Streamlit chat UI (Phase 8).

Ask in natural language → SQL → validate → Snowflake → table results.
Charts + AI insights arrive in Phases 9–10.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

st.set_page_config(
    page_title="AI Business Analytics Copilot",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    # Each item: {role, content, turn?}
    st.session_state.messages = []
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None


def _conversation_context() -> list[dict]:
    """Prior successful turns for follow-up resolution (e.g. 'their profit')."""
    ctx = []
    for msg in st.session_state.messages:
        if msg.get("role") != "assistant":
            continue
        turn = msg.get("turn")
        if not turn or not turn.get("sql"):
            continue
        ctx.append(
            {
                "question": turn.get("question"),
                "user_question": turn.get("question"),
                "sql": turn.get("sql"),
                "generated_sql": turn.get("sql"),
                "result_summary": turn.get("result_summary") or "",
            }
        )
    return ctx[-4:]


def _run_question(question: str, provider: str) -> None:
    from src.analytics_pipeline import run_analytics_question, turn_to_history_entry

    st.session_state.messages.append({"role": "user", "content": question})
    with st.spinner("Analyzing with Snowflake…"):
        turn = run_analytics_question(
            question,
            conversation_context=_conversation_context(),
            provider=provider,
            log_to_snowflake=True,
        )
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": turn.message,
            "turn": turn_to_history_entry(turn),
            "dataframe": turn.dataframe,
        }
    )


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("AI Business Analytics Copilot")
    st.caption("Snowflake · Superstore retail analytics")
    st.divider()

    st.subheader("Data source")
    st.write("CRM · ERP · Product Master → `ANALYTICS_AI_DB`")

    try:
        from src.snowflake_connection import clear_connection_cache, healthcheck

        if st.button("Refresh connection", use_container_width=True):
            clear_connection_cache()
            st.session_state.pop("_sf_health", None)
        if "_sf_health" not in st.session_state:
            st.session_state["_sf_health"] = healthcheck()
        health = st.session_state["_sf_health"]
        if health.get("ok"):
            st.success(f"Connected ({health.get('mode')})")
            st.caption(
                f"{health.get('database')}.{health.get('schema')} · "
                f"{health.get('warehouse')} · {health.get('sales_rows', '—')} sales rows"
            )
        else:
            st.warning("Snowflake not connected")
            st.caption(health.get("error") or "")
    except Exception as exc:
        st.error(str(exc))

    st.divider()
    st.subheader("Available analytics")
    from src.metadata import get_sample_questions

    samples = get_sample_questions()
    by_cat: dict[str, list] = defaultdict(list)
    for row in samples:
        by_cat[row.get("CATEGORY") or "Other"].append(row.get("QUESTION") or "")

    for category, questions in by_cat.items():
        with st.expander(category, expanded=(category == "Revenue")):
            for q in questions:
                if st.button(q, key=f"side_{category}_{q}", use_container_width=True):
                    st.session_state.pending_question = q

    st.divider()
    provider = st.selectbox(
        "SQL engine",
        options=["heuristic", "snowflake_cortex", "openai", "auto"],
        index=0,
        help="Use heuristic locally; snowflake_cortex inside Snowflake Streamlit",
    )

    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pending_question = None
        st.rerun()

    st.divider()
    st.subheader("About")
    st.caption(
        "Natural language → validated read-only SQL → Snowflake. "
        "Phases 1–10 complete. Default analytics polish + tests next."
    )

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
st.title("AI Business Analytics Copilot")
st.caption("Ask questions about your business data in natural language.")

# Suggested analytics (main page)
st.markdown("### Suggested Analytics")
main_suggestions = [
    ("Revenue", "What is total revenue?"),
    ("Trend", "Show monthly revenue trend"),
    ("Region", "Show revenue by region"),
    ("Category", "Show revenue by category"),
    ("Top products", "What are the top 10 products by revenue?"),
    ("Profit", "What are the top 10 products by profit?"),
    ("Losses", "Which products have negative profit?"),
    ("Customers", "Who are the top 10 customers by revenue?"),
    ("Segment", "Show revenue by customer segment"),
    ("Margin", "Show profit margin by category"),
]
sug_cols = st.columns(5)
for i, (label, q) in enumerate(main_suggestions):
    if sug_cols[i % 5].button(label, key=f"sug_{i}", help=q, use_container_width=True):
        st.session_state.pending_question = q

st.divider()
st.markdown("### Chat")

# Render history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            turn = msg.get("turn") or {}
            status = turn.get("status")
            if status == "success":
                st.markdown(msg["content"])
                df = msg.get("dataframe")
                turn_q = turn.get("question") or ""
                if df is not None and not df.empty:
                    from src.visualization import (
                        choose_visualization,
                        describe_visualization,
                        render_visualization,
                    )

                    viz = choose_visualization(df, turn_q)
                    st.caption(f"Visualization: {describe_visualization(viz)}")
                    render_visualization(
                        df,
                        viz_type=viz,
                        question=turn_q,
                        title=turn_q,
                        key=f"viz_{id(msg)}",
                    )
                if turn.get("insight"):
                    st.markdown("### Business Insight")
                    st.write(turn["insight"])
                    st.caption(f"insight provider={turn.get('insight_provider')}")
                if turn.get("sql"):
                    with st.expander("View SQL"):
                        st.code(turn["sql"], language="sql")
                        st.caption(
                            f"provider={turn.get('provider')} · "
                            f"gen {turn.get('generation_ms', 0):.0f} ms · "
                            f"Snowflake {turn.get('execution_ms', 0):.0f} ms · "
                            f"insight {turn.get('insight_ms', 0):.0f} ms"
                        )
            elif status == "empty":
                st.info(msg["content"])
                if turn.get("sql"):
                    with st.expander("View SQL"):
                        st.code(turn["sql"], language="sql")
            else:
                st.error(msg["content"])
                if turn.get("sql"):
                    with st.expander("View SQL"):
                        st.code(turn["sql"], language="sql")
            for w in turn.get("warnings") or []:
                st.caption(w)

# Handle pending suggestion click
if st.session_state.pending_question:
    q = st.session_state.pending_question
    st.session_state.pending_question = None
    _run_question(q, provider)
    st.rerun()

# Chat input
prompt = st.chat_input("Ask about sales, profit, products, regions…")
if prompt:
    _run_question(prompt, provider)
    st.rerun()
