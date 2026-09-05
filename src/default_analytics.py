"""
Default / suggested analytics (Phase 11).

Every suggestion is a natural-language question that flows through the same
NL → SQL → validate → execute pipeline (no separate hard-coded dashboards).
"""

from __future__ import annotations

from typing import Any

# Spec §15 — Suggested Analytics
DEFAULT_ANALYTICS: list[dict[str, Any]] = [
    # Revenue
    {
        "id": "total_revenue",
        "category": "Revenue",
        "label": "Total Revenue",
        "question": "What is total revenue?",
        "sort_order": 1,
    },
    {
        "id": "monthly_revenue_trend",
        "category": "Revenue",
        "label": "Monthly Revenue Trend",
        "question": "Show monthly revenue trend",
        "sort_order": 2,
    },
    {
        "id": "revenue_by_region",
        "category": "Revenue",
        "label": "Revenue by Region",
        "question": "Show revenue by region",
        "sort_order": 3,
    },
    {
        "id": "revenue_by_category",
        "category": "Revenue",
        "label": "Revenue by Category",
        "question": "Show revenue by category",
        "sort_order": 4,
    },
    # Products
    {
        "id": "top10_products_revenue",
        "category": "Products",
        "label": "Top 10 Products by Revenue",
        "question": "What are the top 10 products by revenue?",
        "sort_order": 5,
    },
    {
        "id": "top10_products_profit",
        "category": "Products",
        "label": "Top 10 Products by Profit",
        "question": "What are the top 10 products by profit?",
        "sort_order": 6,
    },
    {
        "id": "negative_profit_products",
        "category": "Products",
        "label": "Products with Negative Profit",
        "question": "Which products have negative profit?",
        "sort_order": 7,
    },
    {
        "id": "all_products_catalog",
        "category": "Products",
        "label": "All Products Available",
        "question": "Provide all products available",
        "sort_order": 7.5,
    },
    # Customers
    {
        "id": "top10_customers_revenue",
        "category": "Customers",
        "label": "Top 10 Customers by Revenue",
        "question": "Who are the top 10 customers by revenue?",
        "sort_order": 8,
    },
    {
        "id": "revenue_by_segment",
        "category": "Customers",
        "label": "Revenue by Customer Segment",
        "question": "Show revenue by customer segment",
        "sort_order": 9,
    },
    # Performance
    {
        "id": "sales_vs_profit",
        "category": "Performance",
        "label": "Sales vs Profit",
        "question": "Compare sales vs profit by category",
        "sort_order": 10,
    },
    {
        "id": "profit_margin_by_category",
        "category": "Performance",
        "label": "Profit Margin by Category",
        "question": "Show profit margin by category",
        "sort_order": 11,
    },
    {
        "id": "monthly_sales_growth",
        "category": "Performance",
        "label": "Monthly Sales Growth",
        "question": "Show monthly sales growth",
        "sort_order": 12,
    },
]

CATEGORY_ORDER = ["Revenue", "Products", "Customers", "Performance"]


def get_default_analytics() -> list[dict[str, Any]]:
    return list(DEFAULT_ANALYTICS)


def get_default_analytics_by_category() -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {c: [] for c in CATEGORY_ORDER}
    for item in DEFAULT_ANALYTICS:
        grouped.setdefault(item["category"], []).append(item)
    return {k: v for k, v in grouped.items() if v}


def find_default_by_id(analytics_id: str) -> dict[str, Any] | None:
    for item in DEFAULT_ANALYTICS:
        if item["id"] == analytics_id:
            return item
    return None
