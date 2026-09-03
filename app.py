"""
AI Business Analytics Copilot — Streamlit entry point.

UI implementation lands in Phase 8. Until then this file documents the target
surface and fails gracefully if opened early.
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="AI Business Analytics Copilot",
    page_icon="📊",
    layout="wide",
)

st.title("AI Business Analytics Copilot")
st.caption("Ask questions about your business data in natural language.")

st.info(
    "Phase 1 is complete (data prep + Snowflake RAW). "
    "Phases 2–7 build curated marts, metadata, SQL generation, validation, "
    "and execution. The full chat UI arrives in Phase 8."
)

st.markdown(
    """
### Current pipeline (target)

1. Suggested analytics / chat question  
2. `generate_sql()` with glossary + metadata  
3. `validate_sql()` — SELECT only  
4. `execute_query()` — read-only Snowflake  
5. Auto visualization + business insight  
6. Optional **View SQL**
"""
)
