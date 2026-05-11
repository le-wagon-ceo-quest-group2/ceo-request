"""Temporal data investigation for online policy design.

Answers:
1. Monthly order volume — sufficient for per-month decisions?
2. New / active sellers per month — sufficient for training?
3. Cold-start IT cost dominance — is profit ever positive in early months?
4. When does the platform reach steady state?
"""

import os
import numpy as np
import pandas as pd

DATA_DIR = os.path.expanduser("~/.lewagon/olist/data/csv")

ALPHA = 3157.27
BETA = 978.23

REVIEW_COST = {1: 100, 2: 50, 3: 40, 4: 0, 5: 0}


def load():
    orders = pd.read_csv(f"{DATA_DIR}/olist_orders_dataset.csv",
                         parse_dates=["order_purchase_timestamp"])
    items = pd.read_csv(f"{DATA_DIR}/olist_order_items_dataset.csv")
    reviews = pd.read_csv(f"{DATA_DIR}/olist_order_reviews_dataset.csv",
                          parse_dates=["review_creation_date"])
    return orders, items, reviews


def build_panel(orders, items, reviews):
    """Per-(seller, month) long table."""
    # Attach purchase month to each item line via order
    item_dates = items.merge(
        orders[["order_id", "order_purchase_timestamp", "order_status"]],
        on="order_id", how="left",
    )
    # Drop cancelled / unavailable orders
    item_dates = item_dates[~item_dates.order_status.isin(["canceled", "unavailable"])]
    item_dates["period"] = item_dates.order_purchase_timestamp.dt.to_period("M")

    seller_month_orders = (
        item_dates.groupby(["seller_id", "period"])
        .agg(
            n_items_t=("order_id", "size"),
            n_orders_t=("order_id", "nunique"),
            sales_t=("price", "sum"),
        )
        .reset_index()
    )

    # Reviews: take latest review per order, attribute to month of creation
    reviews_latest = (
        reviews.sort_values("review_creation_date")
        .groupby("order_id", as_index=False)
        .tail(1)[["order_id", "review_score", "review_creation_date"]]
    )
    reviews_latest["period"] = reviews_latest.review_creation_date.dt.to_period("M")

    # Map review to seller via order_items (de-duped to (order, seller))
    order_seller = items[["order_id", "seller_id"]].drop_duplicates()
    rev_attributed = reviews_latest.merge(order_seller, on="order_id", how="inner")
    rev_attributed["review_cost"] = rev_attributed.review_score.map(REVIEW_COST)

    seller_month_reviews = (
        rev_attributed.groupby(["seller_id", "period"])
        .agg(
            n_reviews_t=("review_score", "size"),
            n_one_star_t=("review_score", lambda s: (s == 1).sum()),
            n_two_star_t=("review_score", lambda s: (s == 2).sum()),
            n_three_star_t=("review_score", lambda s: (s == 3).sum()),
            n_four_star_t=("review_score", lambda s: (s == 4).sum()),
            n_five_star_t=("review_score", lambda s: (s == 5).sum()),
            review_cost_t=("review_cost", "sum"),
        )
        .reset_index()
    )

    panel = seller_month_orders.merge(
        seller_month_reviews,
        on=["seller_id", "period"],
        how="outer",
    ).fillna(0)
    return panel


def monthly_aggregate(panel):
    """Aggregate to month level."""
    agg = (
        panel.groupby("period")
        .agg(
            sellers_active=("seller_id", "nunique"),
            n_orders=("n_orders_t", "sum"),
            n_items=("n_items_t", "sum"),
            sales=("sales_t", "sum"),
            n_reviews=("n_reviews_t", "sum"),
            review_cost=("review_cost_t", "sum"),
        )
        .sort_index()
    )

    # New sellers per month
    first_month = panel.groupby("seller_id").period.min()
    agg["sellers_new"] = first_month.value_counts().reindex(agg.index, fill_value=0)

    # Cumulative
    agg["cum_sellers"] = (
        first_month.value_counts().sort_index().reindex(agg.index, fill_value=0).cumsum()
    )
    agg["cum_items"] = agg.n_items.cumsum()

    # Per-month income / cost
    agg["sales_fee"] = agg.sales * 0.10
    agg["sub_fee"] = agg.sellers_active * 80
    agg["pre_it_profit"] = agg.sales_fee + agg.sub_fee - agg.review_cost

    # IT cost (cumulative under formula)
    agg["it_cost_cum"] = ALPHA * np.sqrt(agg.cum_sellers) + BETA * np.sqrt(agg.cum_items)
    agg["it_cost_marginal"] = agg.it_cost_cum.diff().fillna(agg.it_cost_cum.iloc[0])

    # Net per month if IT cost is allocated by marginal
    agg["post_it_marginal"] = agg.pre_it_profit - agg.it_cost_marginal

    # Cumulative pre-IT profit
    agg["cum_pre_it_profit"] = agg.pre_it_profit.cumsum()
    agg["cum_post_it_profit"] = agg.cum_pre_it_profit - agg.it_cost_cum

    return agg


def main():
    print("Loading...")
    orders, items, reviews = load()
    print(f"  orders : {len(orders):,}")
    print(f"  items  : {len(items):,}")
    print(f"  reviews: {len(reviews):,}\n")

    print("Building panel...")
    panel = build_panel(orders, items, reviews)
    print(f"  panel rows: {len(panel):,}")
    print(f"  unique sellers: {panel.seller_id.nunique():,}")
    print(f"  unique periods: {panel.period.nunique()}\n")

    print("Aggregating monthly...")
    agg = monthly_aggregate(panel)

    pd.set_option("display.max_rows", 30)
    pd.set_option("display.width", 200)
    pd.set_option("display.float_format", "{:,.0f}".format)

    print("\n=== Monthly summary ===")
    cols = [
        "sellers_active", "sellers_new", "cum_sellers",
        "n_orders", "n_items", "sales",
        "review_cost", "pre_it_profit",
        "it_cost_cum", "it_cost_marginal", "post_it_marginal",
        "cum_pre_it_profit", "cum_post_it_profit",
    ]
    print(agg[cols].to_string())

    print("\n=== Cold-start diagnosis ===")
    first_positive_post = agg[agg.cum_post_it_profit > 0]
    if len(first_positive_post) > 0:
        first_p = first_positive_post.index[0]
        print(f"Cum post-IT profit first turns positive at: {first_p}")
        print(f"  cum_sellers at that point: {agg.loc[first_p, 'cum_sellers']:.0f}")
        print(f"  cum_items at that point:   {agg.loc[first_p, 'cum_items']:.0f}")
    else:
        print("Cum post-IT profit NEVER turns positive over the horizon")

    early = agg[agg.it_cost_marginal > agg.pre_it_profit]
    print(f"\nMonths where marginal IT cost > pre-IT profit: {len(early)} of {len(agg)}")
    if len(early) > 0:
        print(early[["sellers_active", "pre_it_profit", "it_cost_marginal"]].head(10).to_string())

    print("\n=== Sufficiency check for monthly decisions ===")
    print("Monthly orders distribution:")
    print(agg.n_orders.describe().to_string())
    print(f"\nMedian active sellers/month: {int(agg.sellers_active.median())}")
    print(f"Median new sellers/month:    {int(agg.sellers_new.median())}")
    print(f"Median orders/month:         {int(agg.n_orders.median())}")
    print(f"Median reviews/month:        {int(agg.n_reviews.median())}")


if __name__ == "__main__":
    main()