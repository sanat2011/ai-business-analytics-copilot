"""Snowflake connection helpers.

Phase 4 will implement full session handling for:
  - local development (env / Streamlit secrets)
  - Snowflake-hosted Streamlit (native session)
"""

from __future__ import annotations


def get_connection():
    raise NotImplementedError("Phase 4 — snowflake_connection.get_connection()")


def get_session():
    """Snowpark session when available."""
    raise NotImplementedError("Phase 4 — snowflake_connection.get_session()")
