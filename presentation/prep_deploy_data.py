"""Pre-compute the data files Soodabeh's & Mario's pages need.

Run once locally; commits the parquet outputs. After this, the Dash app no
longer needs the `olist/` package or the raw CSVs at runtime — everything
loads from `presentation/../data/*.parquet`.

Run:
    python presentation/prep_deploy_data.py
"""

import os
import sys
import json

import numpy as np
import pandas as pd
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
# 4 levels up: presentation → data-olist_ceo_request → 03-Logistic-Regression → 03-Decision-Science
DECISION_SCIENCE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
if DECISION_SCIENCE not in sys.path:
    sys.path.insert(0, DECISION_SCIENCE)

from olist.seller import Seller  # noqa: E402

DATA_DIR = os.path.expanduser("~/.lewagon/olist/data/csv")
OUT_DIR = os.path.normpath(os.path.join(HERE, "..", "data"))
os.makedirs(OUT_DIR, exist_ok=True)


def build_sellers_for_dash():
    """sellers table with `profits / revenues / cost_of_reviews` materialised."""
    sellers = Seller().get_training_data()
    meta = pd.read_parquet(os.path.join(OUT_DIR, "sellers_meta.parquet"))
    sellers = sellers.merge(
        meta[["seller_id", "total_review_cost"]], on="seller_id", how="left"
    )
    sellers["cost_of_reviews"] = sellers["total_review_cost"].fillna(0.0)
    sellers["revenues"] = sellers["sales"] * 0.10 + sellers["months_on_olist"] * 80
    sellers["profits"] = sellers["revenues"] - sellers["cost_of_reviews"]

    path = os.path.join(OUT_DIR, "sellers_for_dash.parquet")
    sellers.to_parquet(path, index=False)
    print(f"  sellers_for_dash.parquet: {len(sellers):,} rows, "
          f"profits range [{sellers.profits.min():,.0f}, {sellers.profits.max():,.0f}]")


def build_state_analysis():
    """Per-state sales + negative-review aggregates."""
    orders = pd.read_csv(
        f"{DATA_DIR}/olist_orders_dataset.csv",
        usecols=["order_id", "customer_id", "order_status"],
    )
    customers = pd.read_csv(
        f"{DATA_DIR}/olist_customers_dataset.csv",
        usecols=["customer_id", "customer_state"],
    )
    items = pd.read_csv(
        f"{DATA_DIR}/olist_order_items_dataset.csv",
        usecols=["order_id", "price", "seller_id"],
    )
    reviews = pd.read_csv(
        f"{DATA_DIR}/olist_order_reviews_dataset.csv",
        usecols=["order_id", "review_score"],
    )

    orders_kept = orders[~orders.order_status.isin(("canceled", "unavailable"))]
    order_state = orders_kept.merge(customers, on="customer_id", how="inner")[
        ["order_id", "customer_state"]
    ]

    items_by_order = items.groupby("order_id", as_index=False)["price"].sum()
    sales_per_order = order_state.merge(items_by_order, on="order_id", how="inner")
    state_sales = (
        sales_per_order.groupby("customer_state", as_index=False)["price"]
        .sum()
        .rename(columns={"price": "sales"})
        .sort_values("sales", ascending=False)
    )
    state_sales["sales_pct"] = state_sales["sales"] / state_sales["sales"].sum() * 100

    reviews_state = reviews.merge(order_state, on="order_id", how="inner")
    reviews_state["is_negative"] = reviews_state["review_score"] <= 3
    review_by_state = (
        reviews_state.groupby("customer_state", as_index=False)
        .agg(
            total_reviews=("review_score", "count"),
            negative_reviews=("is_negative", "sum"),
        )
    )
    review_by_state["negative_review_pct"] = (
        review_by_state["negative_reviews"] / review_by_state["total_reviews"] * 100
    ).round(2)

    state = state_sales.merge(review_by_state, on="customer_state", how="left")
    path = os.path.join(OUT_DIR, "state_analysis.parquet")
    state.to_parquet(path, index=False)
    print(f"  state_analysis.parquet: {len(state)} states")

    # Constants page-level metrics rely on
    single_seller_orders = items.groupby("order_id")["seller_id"].nunique()
    multi_seller_pct = float(
        (1 - (single_seller_orders == 1).sum() / len(single_seller_orders)) * 100
    )
    constants = pd.DataFrame([{"name": "multi_seller_pct", "value": multi_seller_pct}])
    constants.to_parquet(os.path.join(OUT_DIR, "constants.parquet"), index=False)
    print(f"  constants.parquet: multi_seller_pct = {multi_seller_pct:.2f}%")


def download_brazil_geojson():
    """Bundle the Brazilian-states GeoJSON so the analysis page works offline."""
    path = os.path.join(OUT_DIR, "brazil-states.geojson")
    if os.path.exists(path):
        print(f"  brazil-states.geojson: already present, skipping")
        return
    url = (
        "https://raw.githubusercontent.com/codeforamerica/click_that_hood/"
        "master/public/data/brazil-states.geojson"
    )
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    with open(path, "w") as f:
        json.dump(r.json(), f)
    print(f"  brazil-states.geojson: downloaded ({os.path.getsize(path) / 1024:.0f} KB)")


def main():
    print("Building deployment data files...")
    build_sellers_for_dash()
    build_state_analysis()
    download_brazil_geojson()
    print("Done.")


if __name__ == "__main__":
    main()
