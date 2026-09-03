"""Suggested analytics page — same pipeline as the main chat."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

st.set_page_config(page_title="Suggested Analytics", layout="wide")
st.title("Suggested Analytics")
st.caption("Every suggestion uses the same NL → SQL → Snowflake pipeline.")

from src.metadata import get_sample_questions

samples = get_sample_questions()
for row in samples:
    q = row.get("QUESTION") or ""
    cat = row.get("CATEGORY") or ""
    if st.button(f"[{cat}] {q}", key=f"page_{q}", use_container_width=True):
        st.session_state.pending_question = q
        st.switch_page("app.py")
