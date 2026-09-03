"""Suggested analytics page — same 12 defaults as the main Copilot."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

st.title("Suggested Analytics")
st.caption("Every suggestion uses the same NL → SQL → Snowflake pipeline.")

from src.default_analytics import get_default_analytics_by_category

if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

for category, items in get_default_analytics_by_category().items():
    st.subheader(category)
    for item in items:
        if st.button(
            item["label"],
            key=f"page_{item['id']}",
            help=item["question"],
            use_container_width=True,
        ):
            st.session_state.pending_question = item["question"]
            st.success(
                f"Queued: {item['question']}. Open the home Copilot page to run it."
            )
