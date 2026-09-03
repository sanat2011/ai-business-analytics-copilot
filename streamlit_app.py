"""
Snowflake Streamlit-in-Snowflake entrypoint.

Configure the SiS app main file as: streamlit_app.py
Runtime: Warehouse (not Container)
Database/Schema: ANALYTICS_AI_DB.AI
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root (repo / app root) is importable for `src.*`
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Execute the canonical Streamlit app module.
# Importing app runs its top-level Streamlit layout (intended).
import app as _copilot_app  # noqa: E402,F401
