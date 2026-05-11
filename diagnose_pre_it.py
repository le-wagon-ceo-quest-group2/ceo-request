"""Diagnose why online strategy reports pre-IT profit > offline upper bound.

Hypothesis: subscription fee accounting is different.
* Offline ('pre_it_profits' column from Seller.get_training_data):
    sub_fee = months_on_olist * 80
  where months_on_olist ≈ (date_last_sale - date_first_sale).days / 30 (rounded)
* Online (this simulator):
    sub_fee = sum over (seller, period) of 80
  where periods are from first_activity_month to last_activity_month (calendar months)

The two diverge because calendar-month counts can exceed day-based rounding.
"""

import os
import sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", ))   # so we can import olist if needed

ALPHA = 3157.27
BETA = 978.23
REVIEW_COST = {1: 100, 2: 50, 3: 40, 4: 0, 5: 0}


def main():
    panel = pd.read_parquet(os.path.join(HERE, "data", "panel_monthly.parquet"))
    meta = pd.read_parquet(os.path.join(HERE, "data", "sellers_meta.parquet"))

    # Coerce period
    if not isinstance(panel.period.iloc[0], pd.Period):
        panel["period"] = pd.PeriodIndex(panel["period"], freq="M")
        meta["onboard_period"] = pd.PeriodIndex(meta["onboard_period"], freq="M")
        meta["last_active_period"] = pd.PeriodIndex(
            meta["last_active_period"], freq="M"
        )

    panel_with_range = panel.merge(
        meta[["seller_id", "onboard_period", "last_active_period"]],
        on="seller_id",
        how="left",
    )
    panel_filtered = panel_with_range[
        (panel_with_range.period >= panel_with_range.onboard_period)
        & (panel_with_range.period <= panel_with_range.last_active_period)
    ].copy()

    # ------- Method A: simulator-style (calendar months) ----------------
    total_calendar_months = len(panel_filtered)
    sub_fee_calendar = total_calendar_months * 80
    sales_fee = panel_filtered.sales_t.sum() * 0.10
    review_cost = panel_filtered.review_cost_t.sum()
    pre_it_calendar = sub_fee_calendar + sales_fee - review_cost

    # ------- Method B: Olist-style (months_on_olist via dates) ----------
    DATA_DIR = os.path.expanduser("~/.lewagon/olist/data/csv")
    orders = pd.read_csv(
        f"{DATA_DIR}/olist_orders_dataset.csv",
        parse_dates=["order_purchase_timestamp"],
    )
    items = pd.read_csv(f"{DATA_DIR}/olist_order_items_dataset.csv")
    orders_kept = orders[~orders.order_status.isin(("canceled", "unavailable"))]

    item_with_date = items.merge(
        orders_kept[["order_id", "order_purchase_timestamp"]],
        on="order_id",
        how="inner",
    )
    sale_dates = item_with_date.groupby("seller_id").agg(
        date_first_sale=("order_purchase_timestamp", "min"),
        date_last_sale=("order_purchase_timestamp", "max"),
    )
    # Olist's months_on_olist formula: round to integer months
    sale_dates["months_on_olist"] = (
        (sale_dates.date_last_sale - sale_dates.date_first_sale).dt.days / 30
    ).round().astype(int)
    total_months_olist = int(sale_dates.months_on_olist.sum())
    sub_fee_olist = total_months_olist * 80

    print("=" * 70)
    print("Subscription fee accounting comparison")
    print("=" * 70)
    print(f"Sellers in scope: {panel_filtered.seller_id.nunique():,}")
    print()
    print("Method A — Calendar months (simulator):")
    print(f"  total panel rows (= months counted): {total_calendar_months:,}")
    print(f"  sub_fee_total                        : {sub_fee_calendar:>15,.0f} BRL")
    print()
    print("Method B — Olist's months_on_olist (day-based):")
    print(f"  total months_on_olist : {total_months_olist:,}")
    print(f"  sub_fee_total         : {sub_fee_olist:>15,.0f} BRL")
    print()
    inflation = sub_fee_calendar - sub_fee_olist
    print(f"Difference (calendar - Olist): {inflation:>+15,.0f} BRL")
    print()
    print("=" * 70)
    print("Pre-IT profit comparison (no drops, full panel)")
    print("=" * 70)
    pre_it_olist_full = sub_fee_olist + sales_fee - review_cost
    print(f"  sales_fee_total      : {sales_fee:>15,.0f}")
    print(f"  review_cost_total    : {review_cost:>15,.0f}")
    print(f"  pre_it (calendar)    : {pre_it_calendar:>15,.0f}  ← simulator basis")
    print(f"  pre_it (Olist months): {pre_it_olist_full:>15,.0f}")
    print(f"  inflation            : {pre_it_calendar - pre_it_olist_full:>+15,.0f}")
    print()
    print("If 'drop all negative-individual-profit sellers' baseline ≈ 1,493,471 BRL,")
    print("that uses Olist months. Adding the inflation gives the 'simulator equivalent':")
    print(f"  1,493,471 + inflation ≈ {1_493_471 + (pre_it_calendar - pre_it_olist_full):,.0f}")
    print()

    # ------- Method C: per-seller diff distribution ----------------------
    rows_per_seller = panel_filtered.groupby("seller_id").size().rename("calendar_months")
    diff_df = sale_dates.join(rows_per_seller, how="inner")
    diff_df["diff"] = diff_df["calendar_months"] - diff_df["months_on_olist"]
    print("=" * 70)
    print("Per-seller diff distribution (calendar - months_on_olist)")
    print("=" * 70)
    print(diff_df["diff"].describe().to_string())
    print(f"\nSellers with diff > 0: {(diff_df['diff'] > 0).sum():,} of {len(diff_df):,}")
    print(f"Sellers with diff = 0: {(diff_df['diff'] == 0).sum():,}")
    print(f"Mean diff per seller : {diff_df['diff'].mean():.2f} months")


if __name__ == "__main__":
    main()
