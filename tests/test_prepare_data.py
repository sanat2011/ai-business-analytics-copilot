"""Phase 1: source CSV shape and referential integrity."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def test_customers_columns():
    df = pd.read_csv(DATA / "customers.csv")
    assert list(df.columns) == [
        "customer_id",
        "customer_name",
        "segment",
        "country",
        "state",
        "city",
        "postal_code",
        "region",
    ]
    assert len(df) > 0
    assert df["customer_id"].is_unique


def test_orders_columns():
    df = pd.read_csv(DATA / "orders.csv")
    assert list(df.columns) == [
        "order_id",
        "order_date",
        "ship_date",
        "ship_mode",
        "customer_id",
        "product_id",
        "quantity",
        "sales",
        "discount",
        "profit",
    ]
    assert len(df) > 0


def test_products_columns():
    df = pd.read_csv(DATA / "products.csv")
    assert list(df.columns) == [
        "product_id",
        "product_name",
        "category",
        "sub_category",
    ]
    assert df["product_id"].is_unique


def test_referential_integrity():
    customers = pd.read_csv(DATA / "customers.csv")
    orders = pd.read_csv(DATA / "orders.csv")
    products = pd.read_csv(DATA / "products.csv")
    assert orders["customer_id"].isin(customers["customer_id"]).all()
    assert orders["product_id"].isin(products["product_id"]).all()
