"""
AI Business Analytics Copilot — Streamlit entry point.

Phases 4–7: connection, NL→SQL, validation, execution.
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
    st.caption("Phases 1–7 ready. Next: full chat UI + charts + insights.")

# ---------------------------------------------------------------------------
# Main — generate → validate → execute
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

run_cols = st.columns([1, 1, 2])
generate_clicked = run_cols[0].button("Generate SQL", type="primary")
run_clicked = run_cols[1].button("Run on Snowflake")

if generate_clicked and question:
    from src.sql_generator import generate_sql_detailed
    from src.sql_validator import validate_sql_detailed

    with st.spinner("Generating SQL…"):
        result = generate_sql_detailed(question, provider=provider)
    st.session_state["_last_sql_result"] = result
    st.session_state["_last_question"] = question
    st.session_state.pop("_last_query_result", None)
    if result.status == "ok":
        st.session_state["_last_validation"] = validate_sql_detailed(result.sql)
    else:
        st.session_state["_last_validation"] = None

if run_clicked:
    from src.query_executor import execute_query
    from src.sql_generator import generate_sql_detailed
    from src.sql_validator import validate_sql_detailed

    q = question or st.session_state.get("_last_question")
    if not q:
        st.warning("Enter a question first.")
    else:
        with st.spinner("Generating, validating, and running on Snowflake…"):
            gen = generate_sql_detailed(q, provider=provider)
            st.session_state["_last_sql_result"] = gen
            st.session_state["_last_question"] = q
            if gen.status != "ok":
                st.session_state["_last_validation"] = None
                st.session_state["_last_query_result"] = None
            else:
                val = validate_sql_detailed(gen.sql)
                st.session_state["_last_validation"] = val
                if val.ok:
                    st.session_state["_last_query_result"] = execute_query(
                        val.sql,
                        user_question=q,
                        skip_validation=True,  # already validated
                    )
                else:
                    st.session_state["_last_query_result"] = None

result = st.session_state.get("_last_sql_result")
validation = st.session_state.get("_last_validation")
query_result = st.session_state.get("_last_query_result")

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
        if validation and not validation.ok:
            st.error(validation.error or "SQL failed safety validation")
            with st.expander("Rejected SQL"):
                st.code(result.sql, language="sql")
        else:
            safe_sql = validation.sql if validation else result.sql
            st.success("SQL validated (read-only SELECT)")
            with st.expander("View SQL", expanded=True):
                st.code(safe_sql, language="sql")
            if validation and validation.warnings:
                for w in validation.warnings:
                    st.info(w)

    if result.warnings:
        for w in result.warnings:
            st.info(w)
    if result.error and result.status != "error":
        st.caption(f"Note: {result.error}")

if query_result is not None:
    st.subheader("Results")
    if not query_result.ok:
        st.error(query_result.error or "Query failed")
    elif query_result.empty:
        st.warning("Query returned no rows.")
    else:
        st.caption(
            f"{query_result.row_count} rows · "
            f"Snowflake {query_result.execution_time_ms:.0f} ms"
        )
        st.dataframe(query_result.dataframe, use_container_width=True)

st.divider()
st.markdown(
    """
### Pipeline progress

1. ~~Suggested analytics / chat question~~ (partial)  
2. ~~`generate_sql()`~~ **Phase 5**  
3. ~~`validate_sql()`~~ **Phase 6**  
4. ~~`execute_query()`~~ **Phase 7**  
5. Auto visualization + business insight → **Phases 9–10**  
6. Full chat UI → **Phase 8**
"""
)
