"""
AI Business Analytics Copilot — Streamlit entry point.

Phase 4: Snowflake connection health (local + SiS).
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
# Sidebar — connection status (Phase 4)
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
    st.subheader("About")
    st.caption(
        "Phases 1–3: data + marts + metadata. "
        "Phase 4: connection. Phases 5–8: SQL → chat UI."
    )

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
health = st.session_state.get("_sf_health") or {}
if health.get("ok"):
    st.success(
        f"Snowflake ready · "
        f"{health.get('sales_rows', '—'):,} rows in ANALYTICS.SALES_ANALYTICS"
        if health.get("sales_rows") is not None
        else "Snowflake ready"
    )
else:
    st.warning(
        "Snowflake connection not verified yet. "
        "Use the sidebar button, or check `.env` / Streamlit secrets / SiS session."
    )

st.info(
    "Next up: Phase 5 (NL → SQL generation). "
    "Suggested analytics and chat UI land in Phases 8–11."
)

st.markdown(
    """
### Pipeline

1. Suggested analytics / chat question  
2. `generate_sql()` with glossary + metadata  
3. `validate_sql()` — SELECT only  
4. `execute_query()` — read-only Snowflake  
5. Auto visualization + business insight  
6. Optional **View SQL**
"""
)
