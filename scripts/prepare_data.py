#!/usr/bin/env python3
"""
Phase 1 — Prepare source extracts from Superstore-style retail data.

Simulates three enterprise sources:
  CRM            → data/customers.csv
  ERP / OMS      → data/orders.csv
  Product Master → data/products.csv

Usage:
  # Preferred: point at a Tableau Sample Superstore CSV (or compatible)
  python scripts/prepare_data.py --source /path/to/SampleSuperstore.csv

  # Or download from a URL you control / trust
  python scripts/prepare_data.py --url https://example.com/SampleSuperstore.csv

  # Demo fallback: generate a Superstore-schema synthetic dataset
  python scripts/prepare_data.py --generate

Does not hard-code analytics answers into the application — CSVs are the
source of truth for loading into Snowflake RAW tables.
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

# Canonical column names used by Tableau Sample Superstore (and close variants)
COLUMN_ALIASES = {
    "order id": "Order ID",
    "order_id": "Order ID",
    "order date": "Order Date",
    "order_date": "Order Date",
    "ship date": "Ship Date",
    "ship_date": "Ship Date",
    "ship mode": "Ship Mode",
    "ship_mode": "Ship Mode",
    "customer id": "Customer ID",
    "customer_id": "Customer ID",
    "customer name": "Customer Name",
    "customer_name": "Customer Name",
    "segment": "Segment",
    "country": "Country",
    "state": "State",
    "city": "City",
    "postal code": "Postal Code",
    "postal_code": "Postal Code",
    "region": "Region",
    "product id": "Product ID",
    "product_id": "Product ID",
    "product name": "Product Name",
    "product_name": "Product Name",
    "category": "Category",
    "sub-category": "Sub-Category",
    "sub_category": "Sub-Category",
    "subcategory": "Sub-Category",
    "sales": "Sales",
    "quantity": "Quantity",
    "discount": "Discount",
    "profit": "Profit",
}

REQUIRED_CANONICAL = [
    "Order ID",
    "Order Date",
    "Ship Date",
    "Ship Mode",
    "Customer ID",
    "Customer Name",
    "Segment",
    "Country",
    "State",
    "City",
    "Postal Code",
    "Region",
    "Product ID",
    "Product Name",
    "Category",
    "Sub-Category",
    "Sales",
    "Quantity",
    "Discount",
    "Profit",
]


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {}
    for col in df.columns:
        key = str(col).strip().lower()
        if key in COLUMN_ALIASES:
            renamed[col] = COLUMN_ALIASES[key]
        else:
            renamed[col] = str(col).strip()
    out = df.rename(columns=renamed)
    missing = [c for c in REQUIRED_CANONICAL if c not in out.columns]
    if missing:
        raise ValueError(
            "Source CSV is missing required Superstore columns: "
            + ", ".join(missing)
        )
    return out


def load_source_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8", low_memory=False)
    return _normalize_columns(df)


def load_source_url(url: str) -> pd.DataFrame:
    import requests

    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text), encoding="utf-8", low_memory=False)
    return _normalize_columns(df)


def generate_superstore_like(seed: int = 42, n_orders: int = 5000) -> pd.DataFrame:
    """
    Generate a Superstore-schema retail dataset for offline demos.

    Distribution roughly mirrors the public Tableau Sample Superstore
    (US regions, Consumer/Corporate/Home Office, Furniture/Office Supplies/Technology).
    """
    rng = np.random.default_rng(seed)

    regions = {
        "West": ["California", "Washington", "Oregon", "Arizona", "Colorado"],
        "East": ["New York", "Pennsylvania", "Massachusetts", "New Jersey", "Maryland"],
        "Central": ["Texas", "Illinois", "Michigan", "Ohio", "Minnesota"],
        "South": ["Florida", "Georgia", "North Carolina", "Virginia", "Tennessee"],
    }
    cities = {
        "California": ["Los Angeles", "San Francisco", "San Diego"],
        "Washington": ["Seattle", "Spokane"],
        "Oregon": ["Portland"],
        "Arizona": ["Phoenix", "Tucson"],
        "Colorado": ["Denver"],
        "New York": ["New York City", "Buffalo"],
        "Pennsylvania": ["Philadelphia", "Pittsburgh"],
        "Massachusetts": ["Boston"],
        "New Jersey": ["Newark"],
        "Maryland": ["Baltimore"],
        "Texas": ["Houston", "Dallas", "Austin"],
        "Illinois": ["Chicago"],
        "Michigan": ["Detroit"],
        "Ohio": ["Columbus", "Cleveland"],
        "Minnesota": ["Minneapolis"],
        "Florida": ["Miami", "Orlando", "Tampa"],
        "Georgia": ["Atlanta"],
        "North Carolina": ["Charlotte", "Raleigh"],
        "Virginia": ["Richmond"],
        "Tennessee": ["Nashville"],
    }
    segments = ["Consumer", "Corporate", "Home Office"]
    ship_modes = ["Standard Class", "Second Class", "First Class", "Same Day"]

    catalog = [
        ("FUR-BO-10001798", "Bush Somerset Collection Bookcase", "Furniture", "Bookcases"),
        ("FUR-CH-10000454", "Hon Deluxe Fabric Upholstered Stacking Chairs", "Furniture", "Chairs"),
        ("FUR-TA-10000577", "Bretford CR4500 Series Slim Rectangular Table", "Furniture", "Tables"),
        ("FUR-FU-10001487", "Eldon Expressions Wood and Plastic Desk Accessories", "Furniture", "Furnishings"),
        ("OFF-LA-10000240", "Self-Adhesive Address Labels for Typewriters", "Office Supplies", "Labels"),
        ("OFF-ST-10000760", "Eldon Fold 'N Roll Cart System", "Office Supplies", "Storage"),
        ("OFF-AR-10002867", "Newell 322", "Office Supplies", "Art"),
        ("OFF-BI-10003910", "DXL Angle-D Binders with Locking Rings", "Office Supplies", "Binders"),
        ("OFF-PA-10002365", "Xerox 1967", "Office Supplies", "Paper"),
        ("OFF-AP-10002311", "Holmes Replacement Filter for HEPA Air Cleaner", "Office Supplies", "Appliances"),
        ("TEC-PH-10002075", "Samsung Galaxy Note 4", "Technology", "Phones"),
        ("TEC-AC-10003027", "Imation 8GB Mini TravelDrive USB 2.0 Flash Drive", "Technology", "Accessories"),
        ("TEC-CO-10001798", "Canon PC1080F Personal Copier", "Technology", "Copiers"),
        ("TEC-MA-10001148", "Okidata C610n Laser Printer", "Technology", "Machines"),
        ("FUR-CH-10004218", "Global Fabric Manager's Chair", "Furniture", "Chairs"),
        ("OFF-EN-10001990", "Staple envelope", "Office Supplies", "Envelopes"),
        ("TEC-PH-10004977", "GE 30524EE4", "Technology", "Phones"),
        ("OFF-BI-10004632", "Ibico Hi-Tech Manual Binding System", "Office Supplies", "Binders"),
        ("FUR-TA-10004575", "Hon 5100 Series Wood Tables", "Furniture", "Tables"),
        ("TEC-AC-10003832", "Logitech G19 Gaming Keyboard", "Technology", "Accessories"),
    ]

    first_names = [
        "Claire", "Darrin", "Sean", "Brosina", "Andrew", "Irene", "Harold",
        "Pete", "Alejandro", "Zuschuss", "Ken", "Sandra", "Emily", "Maria",
        "John", "Lisa", "Robert", "Patricia", "Michael", "Jennifer",
    ]
    last_names = [
        "Gute", "Van", "O'Donnell", "Eckert", "Allen", "Watkins", "Gonzalez",
        "Kriz", "Davies", "Donatelli", "Lonsdale", "Flake", "Nguyen", "Chen",
        "Patel", "Smith", "Johnson", "Williams", "Brown", "Jones",
    ]

    n_customers = 500
    customer_rows = []
    for i in range(n_customers):
        region = rng.choice(list(regions.keys()))
        state = rng.choice(regions[region])
        city = rng.choice(cities[state])
        cid = f"CG-{10000 + i}"
        name = f"{rng.choice(first_names)} {rng.choice(last_names)}"
        customer_rows.append(
            {
                "Customer ID": cid,
                "Customer Name": name,
                "Segment": rng.choice(segments, p=[0.52, 0.30, 0.18]),
                "Country": "United States",
                "State": state,
                "City": city,
                "Postal Code": str(int(rng.integers(10000, 99999))),
                "Region": region,
            }
        )
    customers = pd.DataFrame(customer_rows)

    rows = []
    start = pd.Timestamp("2021-01-01")
    end = pd.Timestamp("2024-12-31")
    days = (end - start).days

    for i in range(n_orders):
        cust = customers.iloc[int(rng.integers(0, len(customers)))]
        prod = catalog[int(rng.integers(0, len(catalog)))]
        order_day = start + pd.Timedelta(days=int(rng.integers(0, days + 1)))
        ship_delay = int(rng.integers(1, 8))
        qty = int(rng.integers(1, 8))
        unit = float(rng.uniform(5, 450))
        discount = float(rng.choice([0.0, 0.1, 0.15, 0.2, 0.3], p=[0.45, 0.25, 0.15, 0.10, 0.05]))
        sales = round(unit * qty * (1 - discount), 2)
        # Some lines intentionally unprofitable (negative profit)
        margin = float(rng.uniform(-0.25, 0.45))
        profit = round(sales * margin, 2)
        order_id = f"CA-202{order_day.year % 10}-{100000 + i}"
        rows.append(
            {
                "Order ID": order_id,
                "Order Date": order_day.strftime("%Y-%m-%d"),
                "Ship Date": (order_day + pd.Timedelta(days=ship_delay)).strftime("%Y-%m-%d"),
                "Ship Mode": rng.choice(ship_modes, p=[0.55, 0.22, 0.16, 0.07]),
                "Customer ID": cust["Customer ID"],
                "Customer Name": cust["Customer Name"],
                "Segment": cust["Segment"],
                "Country": cust["Country"],
                "State": cust["State"],
                "City": cust["City"],
                "Postal Code": cust["Postal Code"],
                "Region": cust["Region"],
                "Product ID": prod[0],
                "Product Name": prod[1],
                "Category": prod[2],
                "Sub-Category": prod[3],
                "Sales": sales,
                "Quantity": qty,
                "Discount": discount,
                "Profit": profit,
            }
        )

    return pd.DataFrame(rows)


def split_sources(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    customers = (
        df[
            [
                "Customer ID",
                "Customer Name",
                "Segment",
                "Country",
                "State",
                "City",
                "Postal Code",
                "Region",
            ]
        ]
        .drop_duplicates(subset=["Customer ID"])
        .rename(
            columns={
                "Customer ID": "customer_id",
                "Customer Name": "customer_name",
                "Segment": "segment",
                "Country": "country",
                "State": "state",
                "City": "city",
                "Postal Code": "postal_code",
                "Region": "region",
            }
        )
        .sort_values("customer_id")
        .reset_index(drop=True)
    )

    products = (
        df[["Product ID", "Product Name", "Category", "Sub-Category"]]
        .drop_duplicates(subset=["Product ID"])
        .rename(
            columns={
                "Product ID": "product_id",
                "Product Name": "product_name",
                "Category": "category",
                "Sub-Category": "sub_category",
            }
        )
        .sort_values("product_id")
        .reset_index(drop=True)
    )

    # Order grain: one row per order line (order_id + product_id)
    orders = (
        df[
            [
                "Order ID",
                "Order Date",
                "Ship Date",
                "Ship Mode",
                "Customer ID",
                "Product ID",
                "Quantity",
                "Sales",
                "Discount",
                "Profit",
            ]
        ]
        .rename(
            columns={
                "Order ID": "order_id",
                "Order Date": "order_date",
                "Ship Date": "ship_date",
                "Ship Mode": "ship_mode",
                "Customer ID": "customer_id",
                "Product ID": "product_id",
                "Quantity": "quantity",
                "Sales": "sales",
                "Discount": "discount",
                "Profit": "profit",
            }
        )
        .reset_index(drop=True)
    )

    return customers, orders, products


def write_extracts(
    customers: pd.DataFrame,
    orders: pd.DataFrame,
    products: pd.DataFrame,
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    customers.to_csv(out_dir / "customers.csv", index=False)
    orders.to_csv(out_dir / "orders.csv", index=False)
    products.to_csv(out_dir / "products.csv", index=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare Superstore source CSVs")
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--source", type=Path, help="Path to Sample Superstore CSV")
    src.add_argument("--url", type=str, help="HTTP(S) URL to Sample Superstore CSV")
    src.add_argument(
        "--generate",
        action="store_true",
        help="Generate Superstore-schema demo data (offline fallback)",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-orders", type=int, default=5000)
    parser.add_argument("--out-dir", type=Path, default=DATA_DIR)
    args = parser.parse_args(argv)

    if args.source:
        print(f"Loading source CSV: {args.source}")
        df = load_source_csv(args.source)
    elif args.url:
        print(f"Downloading source CSV: {args.url}")
        df = load_source_url(args.url)
    elif args.generate:
        print(f"Generating Superstore-like dataset (n_orders={args.n_orders})…")
        df = generate_superstore_like(seed=args.seed, n_orders=args.n_orders)
    else:
        # Default: generate so Phase 1 works without network
        print("No --source/--url provided; generating demo Superstore-like data.")
        print("Tip: pass --source SampleSuperstore.csv to use the public Tableau file.")
        df = generate_superstore_like(seed=args.seed, n_orders=args.n_orders)

    customers, orders, products = split_sources(df)
    write_extracts(customers, orders, products, args.out_dir)

    print(f"Wrote {args.out_dir / 'customers.csv'}  ({len(customers):,} customers)")
    print(f"Wrote {args.out_dir / 'orders.csv'}     ({len(orders):,} order lines)")
    print(f"Wrote {args.out_dir / 'products.csv'}   ({len(products):,} products)")
    print("Phase 1 data preparation complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
