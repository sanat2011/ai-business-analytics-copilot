"""Phase 9 — visualization selection tests."""

from __future__ import annotations

import pandas as pd

from src.visualization import choose_visualization, describe_visualization


def test_kpi_single_numeric():
    df = pd.DataFrame({"TOTAL_REVENUE": [1000.0]})
    assert choose_visualization(df) == "kpi"


def test_line_monthly():
    df = pd.DataFrame(
        {
            "ORDER_MONTH": pd.date_range("2024-01-01", periods=6, freq="MS"),
            "REVENUE": [1, 2, 3, 4, 5, 6],
        }
    )
    assert choose_visualization(df, "Show monthly revenue trend") == "line"


def test_bar_by_region():
    df = pd.DataFrame(
        {"REGION": ["West", "East", "Central", "South"], "TOTAL_REVENUE": [4, 3, 2, 1]}
    )
    assert choose_visualization(df, "Show revenue by region") == "bar"


def test_pie_percentage_contribution():
    df = pd.DataFrame(
        {
            "CATEGORY": ["Furniture", "Technology", "Office Supplies"],
            "PCT_OF_SALES": [0.3, 0.4, 0.3],
        }
    )
    assert choose_visualization(df, "What percentage of sales comes from each category?") == "pie"


def test_table_large():
    df = pd.DataFrame(
        {
            "PRODUCT_NAME": [f"P{i}" for i in range(80)],
            "TOTAL_SALES": list(range(80)),
        }
    )
    assert choose_visualization(df) == "table"


def test_empty():
    assert choose_visualization(pd.DataFrame()) == "empty"


def test_describe():
    assert "Bar" in describe_visualization("bar")
