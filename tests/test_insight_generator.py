"""Phase 10 — insight generator tests."""

from __future__ import annotations

import pandas as pd

from src.insight_generator import generate_insight, heuristic_insight


def test_kpi_insight():
    df = pd.DataFrame({"TOTAL_REVENUE": [4201961.0]})
    text = generate_insight("What is total revenue?", df, provider="heuristic")
    assert "4201961" in text.replace(",", "")
    assert "TOTAL REVENUE" in text.upper() or "Total Revenue" in text


def test_top_comparison_insight():
    df = pd.DataFrame(
        {
            "PRODUCT_NAME": ["A", "B", "C"],
            "TOTAL_SALES": [120000.0, 110000.0, 90000.0],
        }
    )
    text = heuristic_insight("What are the top 5 products by sales?", df)
    assert "A" in text
    assert "B" in text
    assert "9" in text or "8." in text  # ~9% ahead


def test_empty_insight():
    text = generate_insight("Anything", pd.DataFrame(), provider="heuristic")
    assert "insufficient" in text.lower()


def test_negative_profit_mentions_count():
    df = pd.DataFrame(
        {
            "PRODUCT_NAME": ["X", "Y"],
            "TOTAL_PROFIT": [-10.0, 5.0],
        }
    )
    text = heuristic_insight("Which products have negative profit?", df)
    assert "negative" in text.lower()
