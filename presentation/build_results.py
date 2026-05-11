"""Run all strategies once and cache their period_log + summary to parquet.

Re-run this whenever the panel data or any strategy changes:

    python presentation/build_results.py

The Dash app reads from ./cache/*.parquet — never re-runs strategies on its own.
"""

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
sys.path.insert(0, PARENT)

from strategy_warmup_3rd_month import run_strategy as run_a  # noqa: E402
from strategy_one_shot_drop import run_strategy as run_b  # noqa: E402
from strategy_no_warmup import run_strategy as run_a_prime  # noqa: E402
from strategy_hybrid import run_strategy as run_c  # noqa: E402

ALPHA = 3157.27
BETA = 978.23

CACHE_DIR = os.path.join(HERE, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def run_keep_all(panel: pd.DataFrame, meta: pd.DataFrame):
    """No-drops baseline."""
    if not isinstance(panel.period.iloc[0], pd.Period):
        panel = panel.copy()
        panel["period"] = pd.PeriodIndex(panel["period"], freq="M")
    if not isinstance(meta.onboard_period.iloc[0], pd.Period):
        meta = meta.copy()
        meta["onboard_period"] = pd.PeriodIndex(meta["onboard_period"], freq="M")
        meta["last_active_period"] = pd.PeriodIndex(
            meta["last_active_period"], freq="M"
        )

    panel = panel.merge(
        meta[["seller_id", "onboard_period", "last_active_period"]],
        on="seller_id",
        how="left",
    )
    panel = panel[
        (panel.period >= panel.onboard_period)
        & (panel.period <= panel.last_active_period)
    ]

    periods = sorted(panel.period.unique())
    cum_pre_it = 0.0
    cum_n = 0
    cum_q = 0.0
    seen: set = set()
    log = []

    for t in periods:
        active = panel[panel.period == t]
        period_profit = (
            active.sales_t.sum() * 0.10
            + active.sub_fee_t.sum()
            - active.review_cost_t.sum()
        )
        cum_pre_it += period_profit
        new_sellers = set(active.seller_id) - seen
        cum_n += len(new_sellers)
        seen |= new_sellers
        cum_q += float(active.n_items_t.sum())
        it_cost = (
            ALPHA * np.sqrt(cum_n) + BETA * np.sqrt(cum_q) if cum_n > 0 else 0.0
        )
        log.append({
            "period": str(t),
            "n_active": len(active),
            "period_profit": period_profit,
            "cum_pre_it": cum_pre_it,
            "cum_n": cum_n,
            "cum_q": cum_q,
            "it_cost": it_cost,
            "cum_post_it": cum_pre_it - it_cost,
            "n_dropped_total": 0,
        })

    final_pre_it = (
        panel.sales_t.sum() * 0.10
        + panel.sub_fee_t.sum()
        - panel.review_cost_t.sum()
    )
    final_n = int(panel.seller_id.nunique())
    final_q = float(panel.n_items_t.sum())
    final_it_cost = ALPHA * np.sqrt(final_n) + BETA * np.sqrt(final_q)
    return {
        "period_log": pd.DataFrame(log),
        "drop_log": pd.DataFrame(columns=["period_dropped", "seller_id"]),
        "total_dropped": 0,
        "final_pre_it_profit": float(final_pre_it),
        "final_it_cost": float(final_it_cost),
        "final_post_it_profit": float(final_pre_it - final_it_cost),
    }


STRATEGIES = {
    "keep_all": run_keep_all,
    "A": run_a,
    "B": run_b,
    "A_prime": run_a_prime,
    "C": run_c,
}


def main():
    panel = pd.read_parquet(os.path.join(PARENT, "data", "panel_monthly.parquet"))
    meta = pd.read_parquet(os.path.join(PARENT, "data", "sellers_meta.parquet"))

    summary_rows = []
    for name, fn in STRATEGIES.items():
        print(f"Running {name}...")
        res = fn(panel, meta)
        log_path = os.path.join(CACHE_DIR, f"period_log_{name}.parquet")
        # Ensure period is string for parquet portability
        log = res["period_log"].copy()
        log["period"] = log["period"].astype(str)
        log.to_parquet(log_path, index=False)
        summary_rows.append({
            "strategy": name,
            "total_dropped": int(res["total_dropped"]),
            "final_pre_it_profit": float(res["final_pre_it_profit"]),
            "final_it_cost": float(res["final_it_cost"]),
            "final_post_it_profit": float(res["final_post_it_profit"]),
        })

    summary = pd.DataFrame(summary_rows)
    summary.to_parquet(os.path.join(CACHE_DIR, "summary.parquet"), index=False)

    pd.set_option("display.float_format", "{:,.0f}".format)
    print("\nSummary:")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
