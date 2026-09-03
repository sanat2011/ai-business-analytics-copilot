"""
Auto-select and render charts / KPIs / tables (Phase 9).

Rules:
  - Single numeric cell → KPI card
  - Time-series (date/month/year + measure) → line chart
  - Categorical comparison → bar chart
  - Percentage composition (small categories) → pie/donut when appropriate
  - Large / ambiguous results → table (with display limit)
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

TIME_NAME_RE = re.compile(
    r"(date|month|year|week|quarter|order_month|order_year|period|day)",
    re.IGNORECASE,
)
PCT_NAME_RE = re.compile(r"(pct|percent|percentage|share|contribution)", re.IGNORECASE)
CAT_HINTS = re.compile(
    r"(region|category|segment|state|city|product|sub_category|sub-category|ship_mode)",
    re.IGNORECASE,
)

DISPLAY_ROW_LIMIT = 200


def _is_datetime_series(s: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(s):
        return True
    if s.dtype == object or pd.api.types.is_string_dtype(s):
        sample = s.dropna().astype(str).head(8)
        if sample.empty:
            return False
        parsed = pd.to_datetime(sample, errors="coerce", utc=False)
        return parsed.notna().mean() >= 0.75
    return False


def _numeric_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]


def _categorical_columns(df: pd.DataFrame) -> list[str]:
    cols = []
    for c in df.columns:
        if c in _numeric_columns(df):
            continue
        if _is_datetime_series(df[c]) or TIME_NAME_RE.search(str(c)):
            continue
        cols.append(c)
    return cols


def _time_columns(df: pd.DataFrame) -> list[str]:
    cols = []
    for c in df.columns:
        if TIME_NAME_RE.search(str(c)) or _is_datetime_series(df[c]):
            cols.append(c)
    return cols


def choose_visualization(df: pd.DataFrame | None, question: str = "") -> str:
    """
    Return one of: kpi | line | bar | pie | table | empty | unsupported
    """
    if df is None:
        return "unsupported"
    if df.empty:
        return "empty"

    q = (question or "").lower()
    n_rows, n_cols = df.shape
    nums = _numeric_columns(df)
    cats = _categorical_columns(df)
    times = _time_columns(df)

    # Single scalar KPI
    if n_rows == 1 and n_cols == 1 and nums:
        return "kpi"
    if n_rows == 1 and len(nums) == 1 and n_cols <= 2:
        return "kpi"

    # Explicit pie intent
    wants_pie = any(
        w in q for w in ("percentage", "percent", "share", "contribution", "composition", "breakdown")
    )
    if wants_pie and cats and nums and 2 <= n_rows <= 12:
        return "pie"

    # Percentage column + category
    pct_cols = [c for c in nums if PCT_NAME_RE.search(str(c))]
    if pct_cols and cats and 2 <= n_rows <= 12:
        return "pie"

    # Time series
    if times and nums and n_rows >= 2:
        return "line"

    # Categorical comparison
    if cats and nums and 2 <= n_rows <= 50:
        return "bar"

    # Question hints
    if any(w in q for w in ("trend", "over time", "monthly", "yearly", "by month", "by year")):
        if nums and n_rows >= 2:
            return "line" if times or any(TIME_NAME_RE.search(str(c)) for c in df.columns) else "bar"

    if cats and nums and n_rows > 50:
        return "table"

    if n_rows <= 30:
        return "table"

    return "table"


def _pick_xy(df: pd.DataFrame) -> tuple[str | None, str | None]:
    nums = _numeric_columns(df)
    times = _time_columns(df)
    cats = _categorical_columns(df)
    y = nums[0] if nums else None
    if times:
        x = times[0]
    elif cats:
        # Prefer columns with categorical name hints
        hinted = [c for c in cats if CAT_HINTS.search(str(c))]
        x = hinted[0] if hinted else cats[0]
    else:
        x = df.columns[0] if len(df.columns) else None
    return x, y


def prepare_display_frame(df: pd.DataFrame, limit: int = DISPLAY_ROW_LIMIT) -> pd.DataFrame:
    if len(df) > limit:
        return df.head(limit).copy()
    return df


def render_visualization(
    df: pd.DataFrame | None,
    viz_type: str | None = None,
    title: str = "",
    question: str = "",
    key: str | None = None,
) -> str:
    """
    Render into the active Streamlit context.
    Returns the visualization type actually used.
    """
    import streamlit as st

    if df is None:
        st.caption("No data to visualize.")
        return "unsupported"
    if df.empty:
        st.info("Empty result — nothing to chart.")
        return "empty"

    viz = viz_type or choose_visualization(df, question)
    display = prepare_display_frame(df)

    if viz == "kpi":
        nums = _numeric_columns(display)
        col = nums[0] if nums else display.columns[0]
        value = display.iloc[0][col]
        label = title or str(col).replace("_", " ").title()
        try:
            st.metric(label=label, value=f"{float(value):,.2f}")
        except Exception:
            st.metric(label=label, value=str(value))
        return "kpi"

    if viz in {"line", "bar", "pie"}:
        try:
            import plotly.express as px
        except ImportError:
            st.warning("Plotly is not installed; showing a table instead.")
            st.dataframe(display, use_container_width=True)
            return "table"

        x, y = _pick_xy(display)
        if not x or not y:
            st.dataframe(display, use_container_width=True)
            return "table"

        chart_title = title or question or ""
        plot_key = key or f"chart_{viz}_{x}_{y}"

        if viz == "line":
            plot_df = display.copy()
            if not pd.api.types.is_datetime64_any_dtype(plot_df[x]):
                converted = pd.to_datetime(plot_df[x], errors="coerce")
                if converted.notna().any():
                    plot_df[x] = converted
            plot_df = plot_df.sort_values(by=x)
            fig = px.line(plot_df, x=x, y=y, title=chart_title, markers=True)
        elif viz == "pie":
            fig = px.pie(display, names=x, values=y, title=chart_title, hole=0.35)
        else:  # bar
            plot_df = display.sort_values(by=y, ascending=False)
            fig = px.bar(plot_df, x=x, y=y, title=chart_title)
            fig.update_layout(xaxis_tickangle=-30)

        fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=420)
        st.plotly_chart(fig, use_container_width=True, key=plot_key)
        with st.expander("Show data table"):
            st.dataframe(display, use_container_width=True)
        return viz

    # table / default
    if len(df) > DISPLAY_ROW_LIMIT:
        st.caption(f"Showing first {DISPLAY_ROW_LIMIT} of {len(df)} rows.")
    st.dataframe(display, use_container_width=True)
    return "table"


def describe_visualization(viz_type: str) -> str:
    return {
        "kpi": "KPI card",
        "line": "Line chart",
        "bar": "Bar chart",
        "pie": "Pie / donut chart",
        "table": "Data table",
        "empty": "Empty result",
        "unsupported": "Unsupported visualization",
    }.get(viz_type, viz_type)
