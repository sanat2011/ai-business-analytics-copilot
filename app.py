"""
AI Business Analytics Copilot — Streamlit entry point.

Phase 4: Snowflake connection health
Phase 5: NL → SQL generation demo
Full chat UI arrives in Phase 8.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

st.set_page_config(
    page_title="AI Business Analytics Copilot",
    page_icon="📊",
    layout="wide",
)

st.title("AI Business Analytics Copilot")
st.caption("Ask questions about your business data in natural language.")

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("AI Business Analytics Copilot")
    st.caption("Data source: Snowflake · Superstore retail")
    st.divider()
    st.subheader("Connection")
    if st.button("Test Snowflake connection", use_container_width=True):
        st.session_state.pop("_sf_health", None)

    try:
        from src.snowflake_connection import clear_connection_cache, healthcheck

        if "_sf_health" not in st.session_state:
            with st.spinner("Connecting to Snowflake…"):
                clear_connection_cache()
                st.session_state["_sf_health"] = healthcheck()
        health = st.session_state["_sf_health"]
        if health.get("ok"):
            st.success(f"Connected ({health.get('mode')})")
            st.write(
                {
                    "database": health.get("database"),
                    "schema": health.get("schema"),
                    "warehouse": health.get("warehouse"),
                    "role": health.get("role"),
                    "sales_rows": health.get("sales_rows"),
                }
            )
        else:
            st.error("Not connected")
            st.caption(health.get("error") or "Unknown error")
    except Exception as exc:
        st.error("Connection module failed")
        st.caption(str(exc))

    st.divider()
    st.subheader("SQL provider")
    provider = st.selectbox(
        "NL→SQL engine",
        options=["heuristic", "snowflake_cortex", "openai", "auto"],
        index=0,
        help="heuristic works offline; cortex uses Snowflake Cortex COMPLETE",
    )
    st.divider()
    st.subheader("About")
    st.caption("Phases 1–5 ready. Next: SQL validation + execution + chat UI.")

# ---------------------------------------------------------------------------
# Main — Phase 5 NL→SQL demo
# ---------------------------------------------------------------------------
st.subheader("Ask a question")
question = st.text_input(
    "Business question",
    placeholder="What are the top 10 products by revenue?",
    label_visibility="collapsed",
)

examples = [
    "What is total revenue?",
    "Show revenue by region",
    "What are the top 10 products by revenue?",
    "Which products have negative profit?",
    "What is average order value?",
]
cols = st.columns(len(examples))
for col, example in zip(cols, examples):
    if col.button(example, use_container_width=True):
        st.session_state["_demo_q"] = example
        question = example

if st.session_state.get("_demo_q") and not question:
    question = st.session_state["_demo_q"]

if st.button("Generate SQL", type="primary") and question:
    from src.sql_generator import generate_sql_detailed

    with st.spinner("Generating SQL…"):
        result = generate_sql_detailed(question, provider=provider)
    st.session_state["_last_sql_result"] = result
    st.session_state["_last_question"] = question

result = st.session_state.get("_last_sql_result")
if result:
    st.markdown(f"**Question:** {st.session_state.get('_last_question', '')}")
    st.caption(
        f"provider={result.provider} · status={result.status} · "
        f"{result.latency_ms:.0f} ms"
    )
    if result.status == "insufficient_data":
        st.warning(
            "I cannot answer this from the current Snowflake dataset "
            "(missing tables/metrics for this question)."
        )
    elif result.status == "error":
        st.error(result.error or "SQL generation failed")
    else:
        st.code(result.sql, language="sql")
    if result.warnings:
        for w in result.warnings:
            st.info(w)
    if result.error and result.status != "error":
        st.caption(f"Note: {result.error}")

st.divider()
st.markdown(
    """
### Pipeline progress

1. ~~Suggested analytics / chat question~~ (partial — Phase 5 demo)  
2. ~~`generate_sql()` with glossary + metadata~~ **Phase 5**  
3. `validate_sql()` — SELECT only → **Phase 6**  
4. `execute_query()` — read-only Snowflake → **Phase 7**  
5. Auto visualization + business insight → **Phases 9–10**  
6. Optional **View SQL**
"""
)
