# Snowflake Streamlit-in-Snowflake entrypoint.
# SiS often expects streamlit_app.py as the main file.
# Keep app.py as the canonical implementation.

from app import *  # noqa: F401,F403
