"""Build (seller, period) monthly panel for online policy simulation.

Output artifacts:

* panel : long DataFrame keyed on (seller_id, period) with monthly metrics
          (n_orders_t, n_items_t, sales_t, n_reviews_t, n_*_star_t,
           review_cost_t). One row per (seller, period) from the seller's
           onboard month through the dataset's last month, with 0s for
           inactive months (dense layout).

* sellers_meta : per-seller metadata (onboard_period, last_active_period,
                 lifetime totals, city/state).

Both are written to ./data/*.parquet for downstream simulator use.

Conventions
-----------

* Period = month (Pandas Period 'M').
* Order status filter: drops 'canceled' and 'unavailable'.
* Review attribution: latest review per order, full cost to each seller
  in that order (TA-confirmed rule, no splitting).
* Review cost time bucket: month of review_creation_date (not order date).
"""

from __future__ import annotations

import os
import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

DATA_DIR_DEFAULT = os.path.expanduser("~/.lewagon/olist/data/csv")

ALPHA = 3157.27
BETA = 978.23

REVIEW_COST = {1: 100, 2: 50, 3: 40, 4: 0, 5: 0}

DROPPED_ORDER_STATUSES = ("canceled", "unavailable")

PANEL_FEATURE_COLS = [
    "n_orders_t",
    "n_items_t",
    "sales_t",
    "n_reviews_t",
    "n_one_star_t",
    "n_two_star_t",
    "n_three_star_t",
    "n_four_star_t",
    "n_five_star_t",
    "review_cost_t",
]

SUB_FEE_PER_MONTH = 80.0  # BRL/month per seller (Olist subscription)


# --------------------------------------------------------------------------- #
# Loaders
# --------------------------------------------------------------------------- #

def load_raw(data_dir: str = DATA_DIR_DEFAULT):
    """Load orders, items, reviews, sellers from the Le Wagon CSV folder."""
    orders = pd.read_csv(
        f"{data_dir}/olist_orders_dataset.csv",
        parse_dates=[
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ],
    )
    items = pd.read_csv(f"{data_dir}/olist_order_items_dataset.csv")
    reviews = pd.read_csv(
        f"{data_dir}/olist_order_reviews_dataset.csv",
        parse_dates=["review_creation_date", "review_answer_timestamp"],
    )
    sellers = pd.read_csv(f"{data_dir}/olist_sellers_dataset.csv")
    return orders, items, reviews, sellers


# --------------------------------------------------------------------------- #
# Internal builders
# --------------------------------------------------------------------------- #

def _attach_period_to_items(orders, items, drop_statuses=DROPPED_ORDER_STATUSES):
    """Each item line gets the month of its order, after status filtering."""
    item_dates = items.merge(
        orders[["order_id", "order_purchase_timestamp", "order_status"]],
        on="order_id",
        how="left",
    )
    item_dates = item_dates[~item_dates.order_status.isin(drop_statuses)].copy()
    item_dates["order_purchase_timestamp"] = pd.to_datetime(
        item_dates["order_purchase_timestamp"], errors="coerce"
    )
    item_dates["period"] = item_dates.order_purchase_timestamp.dt.to_period("M")
    return item_dates


def _build_orders_features(item_dates):
    """(seller, period) -> n_orders_t, n_items_t, sales_t."""
    return (
        item_dates.groupby(["seller_id", "period"])
        .agg(
            n_orders_t=("order_id", "nunique"),
            n_items_t=("order_id", "size"),
            sales_t=("price", "sum"),
        )
        .reset_index()
    )


def _build_review_features(items, reviews):
    """(seller, period) -> review counts and cost.

    Review attribution rule (TA-confirmed):
      * One review per order: take latest by review_creation_date.
      * Multi-seller order: full cost to each seller (no splitting).
    """
    # Coerce review_creation_date to datetime (raw CSV may store as string)
    reviews = reviews.copy()
    reviews["review_creation_date"] = pd.to_datetime(
        reviews["review_creation_date"], errors="coerce"
    )

    # Latest review per order
    reviews_latest = (
        reviews.dropna(subset=["review_creation_date"])
        .sort_values("review_creation_date")
        .groupby("order_id", as_index=False)
        .tail(1)[["order_id", "review_score", "review_creation_date"]]
    )
    reviews_latest["period"] = reviews_latest.review_creation_date.dt.to_period("M")
    reviews_latest["review_cost"] = reviews_latest.review_score.map(REVIEW_COST)

    # One row per (order, seller) regardless of item count
    order_seller = items[["order_id", "seller_id"]].drop_duplicates()
    rev = reviews_latest.merge(order_seller, on="order_id", how="inner")

    return (
        rev.groupby(["seller_id", "period"])
        .agg(
            n_reviews_t=("review_score", "size"),
            n_one_star_t=("review_score", lambda s: int((s == 1).sum())),
            n_two_star_t=("review_score", lambda s: int((s == 2).sum())),
            n_three_star_t=("review_score", lambda s: int((s == 3).sum())),
            n_four_star_t=("review_score", lambda s: int((s == 4).sum())),
            n_five_star_t=("review_score", lambda s: int((s == 5).sum())),
            review_cost_t=("review_cost", "sum"),
        )
        .reset_index()
    )


def _densify(panel: pd.DataFrame) -> pd.DataFrame:
    """Add zero rows for inactive months between each seller's onboard and last_active.

    Note: per-seller right bound is the seller's own last activity month,
    NOT the dataset's last period. This avoids generating "ghost" rows for
    sellers who churned naturally before the data ends.
    """
    bounds = panel.groupby("seller_id").period.agg(["min", "max"])
    bounds.columns = ["onboard", "last_active"]

    skeleton_rows = []
    for sid, row in bounds.iterrows():
        for p in pd.period_range(row["onboard"], row["last_active"], freq="M"):
            skeleton_rows.append((sid, p))
    skeleton = pd.MultiIndex.from_tuples(
        skeleton_rows, names=["seller_id", "period"]
    )

    dense = (
        panel.set_index(["seller_id", "period"])
        .reindex(skeleton)
        .reset_index()
    )
    dense[PANEL_FEATURE_COLS] = dense[PANEL_FEATURE_COLS].fillna(0)
    return dense


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def build_panel(
    orders: pd.DataFrame,
    items: pd.DataFrame,
    reviews: pd.DataFrame,
    sparse: bool = False,
    drop_statuses=DROPPED_ORDER_STATUSES,
) -> pd.DataFrame:
    """Build (seller_id, period) monthly long panel.

    Parameters
    ----------
    sparse : bool, default False
        If False (default), output is dense — one row per (seller, period)
        from onboard month through dataset end, with 0s for inactive months.
        If True, only rows where the seller had orders OR reviews.
    drop_statuses : tuple of str
        Order statuses to exclude (default: 'canceled', 'unavailable').
    """
    item_dates = _attach_period_to_items(orders, items, drop_statuses)
    orders_feat = _build_orders_features(item_dates)
    review_feat = _build_review_features(items, reviews)

    panel = orders_feat.merge(
        review_feat, on=["seller_id", "period"], how="outer"
    )
    panel[PANEL_FEATURE_COLS] = panel[PANEL_FEATURE_COLS].fillna(0)

    if not sparse:
        panel = _densify(panel)

    panel = panel.sort_values(["seller_id", "period"]).reset_index(drop=True)
    return panel


def build_sellers_meta(
    panel: pd.DataFrame,
    sellers: pd.DataFrame,
    orders: pd.DataFrame = None,
    items: pd.DataFrame = None,
    drop_statuses=DROPPED_ORDER_STATUSES,
) -> pd.DataFrame:
    """Per-seller metadata.

    If `orders` and `items` are provided, also computes Olist's official
    `months_on_olist = round((date_last_sale - date_first_sale).days / 30)`.
    This is the day-based formula used by `Seller.get_training_data()`,
    which can differ from calendar-month counts by ~1.27 months on average.
    """
    # Onboard = first period with activity (orders OR reviews)
    active_mask = (panel.n_orders_t > 0) | (panel.n_reviews_t > 0)
    active_panel = panel[active_mask]

    by_seller = (
        active_panel.groupby("seller_id")
        .agg(
            onboard_period=("period", "min"),
            last_active_period=("period", "max"),
            n_active_periods=("period", "size"),
            total_orders=("n_orders_t", "sum"),
            total_items=("n_items_t", "sum"),
            total_sales=("sales_t", "sum"),
            total_review_cost=("review_cost_t", "sum"),
            total_one_star=("n_one_star_t", "sum"),
            total_five_star=("n_five_star_t", "sum"),
        )
        .reset_index()
    )

    meta = by_seller.merge(
        sellers[["seller_id", "seller_city", "seller_state"]],
        on="seller_id",
        how="left",
    )

    if orders is not None and items is not None:
        sale_dates = _compute_olist_months_on_olist(
            orders, items, drop_statuses=drop_statuses
        )
        meta = meta.merge(sale_dates, on="seller_id", how="left")
        # Sellers with no sale dates (review-only) → 0 months
        meta["months_on_olist"] = meta["months_on_olist"].fillna(0).astype(int)

    return meta


def _compute_olist_months_on_olist(orders, items, drop_statuses=DROPPED_ORDER_STATUSES):
    """Per-seller months_on_olist using Olist's day-based formula."""
    orders = orders.copy()
    orders["order_purchase_timestamp"] = pd.to_datetime(
        orders["order_purchase_timestamp"], errors="coerce"
    )
    orders_kept = orders[~orders.order_status.isin(drop_statuses)]

    item_dates = items.merge(
        orders_kept[["order_id", "order_purchase_timestamp"]],
        on="order_id",
        how="inner",
    )
    sale_dates = (
        item_dates.groupby("seller_id")
        .agg(
            date_first_sale=("order_purchase_timestamp", "min"),
            date_last_sale=("order_purchase_timestamp", "max"),
        )
        .reset_index()
    )
    sale_dates["months_on_olist"] = (
        (sale_dates.date_last_sale - sale_dates.date_first_sale).dt.days / 30
    ).round().astype(int)
    return sale_dates[["seller_id", "months_on_olist"]]


def augment_panel_with_sub_fee(panel: pd.DataFrame, meta: pd.DataFrame) -> pd.DataFrame:
    """Add per-period subscription fee column using Olist's months_on_olist.

    For each (seller, period) row, sub_fee_t = months_on_olist * 80 / calendar_count,
    so summing across the seller's full panel recovers months_on_olist * 80.
    """
    if "months_on_olist" not in meta.columns:
        raise ValueError("meta must include 'months_on_olist' column")

    panel = panel.copy()
    calendar_count = panel.groupby("seller_id").size().rename("calendar_count")
    months_map = meta.set_index("seller_id")["months_on_olist"]

    panel = panel.merge(
        calendar_count.reset_index(), on="seller_id", how="left"
    )
    panel["months_on_olist"] = panel.seller_id.map(months_map)
    # Avoid division by zero
    panel["sub_fee_t"] = np.where(
        panel.calendar_count > 0,
        panel.months_on_olist * SUB_FEE_PER_MONTH / panel.calendar_count,
        0.0,
    )
    return panel.drop(columns=["calendar_count", "months_on_olist"])


def sanity_check(
    panel: pd.DataFrame,
    orders: pd.DataFrame,
    items: pd.DataFrame,
    reviews: pd.DataFrame,
    drop_statuses=DROPPED_ORDER_STATUSES,
) -> dict:
    """Verify that panel aggregates match the raw data."""
    item_dates = _attach_period_to_items(orders, items, drop_statuses)

    n_items_raw = len(item_dates)
    sales_raw = float(item_dates.price.sum())

    # For orders, panel.n_orders_t is per-seller-per-month, so sum equals
    # # of distinct (order, seller) pairs in raw.
    pair_count_raw = (
        items[["order_id", "seller_id"]]
        .drop_duplicates()
        .merge(
            orders[["order_id", "order_status"]],
            on="order_id",
            how="left",
        )
        .pipe(lambda df: df[~df.order_status.isin(drop_statuses)])
    )
    n_pairs_raw = len(pair_count_raw)

    return {
        "n_items_raw": n_items_raw,
        "n_items_panel": int(panel.n_items_t.sum()),
        "items_match": n_items_raw == int(panel.n_items_t.sum()),
        "sales_raw": sales_raw,
        "sales_panel": float(panel.sales_t.sum()),
        "sales_close": abs(sales_raw - float(panel.sales_t.sum())) < 0.01,
        "n_order_seller_pairs_raw": n_pairs_raw,
        "n_orders_panel_sum": int(panel.n_orders_t.sum()),
        "orders_match": n_pairs_raw == int(panel.n_orders_t.sum()),
        "n_sellers_panel": int(panel.seller_id.nunique()),
        "n_periods_panel": int(panel.period.nunique()),
        "first_period": str(panel.period.min()),
        "last_period": str(panel.period.max()),
    }


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(script_dir, "data")
    os.makedirs(out_dir, exist_ok=True)

    print("Loading raw data...")
    orders, items, reviews, sellers = load_raw()
    print(f"  orders : {len(orders):,}")
    print(f"  items  : {len(items):,}")
    print(f"  reviews: {len(reviews):,}")
    print(f"  sellers: {len(sellers):,}")

    print("\nBuilding panel (dense)...")
    panel = build_panel(orders, items, reviews, sparse=False)
    print(f"  rows: {len(panel):,}")
    print(f"  unique sellers: {panel.seller_id.nunique():,}")
    print(f"  periods: {panel.period.nunique()} ({panel.period.min()} → {panel.period.max()})")

    print("\nBuilding seller meta (with months_on_olist)...")
    meta = build_sellers_meta(panel, sellers, orders=orders, items=items)
    print(f"  rows: {len(meta):,}")
    print(f"  total months_on_olist: {int(meta.months_on_olist.sum()):,}")

    print("\nAugmenting panel with sub_fee_t...")
    panel = augment_panel_with_sub_fee(panel, meta)
    print(f"  total sub_fee from panel: "
          f"{panel.sub_fee_t.sum():,.0f} BRL "
          f"(should equal months_on_olist*80 = "
          f"{meta.months_on_olist.sum() * SUB_FEE_PER_MONTH:,.0f})")

    print("\nSanity check:")
    checks = sanity_check(panel, orders, items, reviews)
    for k, v in checks.items():
        marker = ""
        if k.endswith(("_match", "_close")) and v is False:
            marker = "  ❌"
        elif k.endswith(("_match", "_close")) and v is True:
            marker = "  ✅"
        print(f"  {k}: {v}{marker}")

    out_panel = os.path.join(out_dir, "panel_monthly.parquet")
    out_meta = os.path.join(out_dir, "sellers_meta.parquet")
    panel.to_parquet(out_panel, index=False)
    meta.to_parquet(out_meta, index=False)
    print(f"\nSaved:")
    print(f"  {out_panel}")
    print(f"  {out_meta}")


if __name__ == "__main__":
    main()