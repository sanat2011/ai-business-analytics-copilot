"""Suggested analytics page — same questions as the main Copilot chat."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

st.title("Suggested Analytics")
st.caption("Click a question, then open the main Copilot page — or use the sidebar there.")

from src.metadata import get_sample_questions

if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

samples = get_sample_questions()
for row in samples:
    q = row.get("QUESTION") or ""
    cat = row.get("CATEGORY") or ""
    if st.button(f"[{cat}] {q}", key=f"page_{q}", use_container_width=True):
        st.session_state.pending_question = q
        st.success(f"Queued: {q}. Open **AI Business Analytics Copilot** (home) to run it.")
