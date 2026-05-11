"""One-shot drop strategy:

  Phase 1 (warmup):    until cumulative post-IT profit turns positive,
                       do not drop any seller.
  Phase 2 (one shot):  at the period when warmup completes, evaluate
                       EVERY currently active seller using all observed
                       data so far. Drop the ones failing the closed-form
                       strong-drop test (under current platform state).
  Phase 3 (passive):   never drop again.

Reports total dropped count and final post-IT profit using
forward-only realised accounting (dropped sellers keep their pre-drop
contributions; only post-drop excluded).
"""

import os
import numpy as np
import pandas as pd

ALPHA = 3157.27
BETA = 978.23


def run_strategy(panel: pd.DataFrame, meta: pd.DataFrame,
                 alpha: float = ALPHA, beta: float = BETA):
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
    ].copy()

    periods = sorted(panel.period.unique())

    dropped: set = set()
    drop_log = []
    period_log = []

    cum_pre_it = 0.0
    cum_n = 0
    cum_q = 0.0
    seen_sellers: set = set()

    warmup_done = False
    warmup_period = None
    one_shot_done = False  # ensures we drop only once

    for t in periods:
        # ---- Step 1: one-shot drop decision at warmup-completion period ----
        # warmup_done was set at end of PREVIOUS period (based on cum_post_it
        # through previous period). So we act here, in the period right
        # after warmup turned positive.
        new_drops: set = set()
        if warmup_done and not one_shot_done:
            # Evaluate every active seller (active = appears in this period,
            # not yet dropped, which is empty at this stage)
            candidates = panel[
                (panel.period <= t)  # have at least 1 month of history through t-1
            ]
            # Group by seller_id: aggregate all observed data so far
            history_per_seller = candidates[candidates.period < t].groupby("seller_id").agg(
                v_obs_sales=("sales_t", "sum"),
                v_obs_sub=("sub_fee_t", "sum"),
                v_obs_review=("review_cost_t", "sum"),
                q_obs=("n_items_t", "sum"),
            )
            history_per_seller["v_obs"] = (
                history_per_seller.v_obs_sales * 0.10
                + history_per_seller.v_obs_sub
                - history_per_seller.v_obs_review
            )

            # Threshold uses platform state at end of t-1 (cum_n, cum_q)
            if cum_n >= 2 and cum_q > 0:
                qi = history_per_seller["q_obs"].values
                # Only consider sellers whose q_obs < cum_q (otherwise sqrt arg is non-positive)
                valid = qi < cum_q
                fixed_marg = alpha * (np.sqrt(cum_n) - np.sqrt(cum_n - 1))
                var_marg = np.where(
                    valid,
                    beta * (np.sqrt(cum_q) - np.sqrt(np.maximum(cum_q - qi, 0.0))),
                    np.inf,
                )
                threshold = fixed_marg + var_marg
                mask = history_per_seller["v_obs"].values < threshold
                # Also require sellers have at least 1 month of observation
                history_per_seller["mask"] = mask & valid
                new_drops = set(history_per_seller[history_per_seller["mask"]].index)

            one_shot_done = True

        dropped |= new_drops
        for sid in new_drops:
            drop_log.append({"period_dropped": t, "seller_id": sid})

        # ---- Step 2: period P&L (forward-only, non-dropped at this period) ----
        active_t = panel[
            (panel.period == t) & (~panel.seller_id.isin(dropped))
        ]
        period_profit = (
            active_t.sales_t.sum() * 0.10
            + active_t.sub_fee_t.sum()
            - active_t.review_cost_t.sum()
        )
        cum_pre_it += period_profit

        # ---- Step 3: update real-time platform state ----
        new_sellers_t = set(active_t.seller_id) - seen_sellers
        cum_n += len(new_sellers_t)
        seen_sellers |= new_sellers_t
        cum_q += float(active_t.n_items_t.sum())

        it_cost_t = (
            alpha * np.sqrt(cum_n) + beta * np.sqrt(cum_q)
            if cum_n > 0
            else 0.0
        )
        cum_post_it_t = cum_pre_it - it_cost_t

        if (not warmup_done) and cum_post_it_t > 0:
            warmup_done = True
            warmup_period = t

        period_log.append({
            "period": str(t),
            "n_active": len(active_t),
            "period_profit": period_profit,
            "cum_pre_it": cum_pre_it,
            "cum_n": cum_n,
            "cum_q": cum_q,
            "it_cost": it_cost_t,
            "cum_post_it": cum_post_it_t,
            "warmup_done": warmup_done,
            "one_shot_done": one_shot_done,
            "n_dropped_this_period": len(new_drops),
            "n_dropped_total": len(dropped),
        })

    # ---- Final forward-only accounting (realised P&L) ----
    drop_period_map = {d["seller_id"]: d["period_dropped"] for d in drop_log}
    panel_with_drop = panel.copy()
    panel_with_drop["_drop_period"] = panel_with_drop.seller_id.map(drop_period_map)
    realised_mask = panel_with_drop["_drop_period"].isna() | (
        panel_with_drop.period < panel_with_drop["_drop_period"]
    )
    realised = panel_with_drop[realised_mask]

    final_n = int(realised.seller_id.nunique())
    final_q = float(realised.n_items_t.sum())
    final_pre_it = (
        realised.sales_t.sum() * 0.10
        + realised.sub_fee_t.sum()
        - realised.review_cost_t.sum()
    )
    final_it_cost = alpha * np.sqrt(final_n) + beta * np.sqrt(final_q)
    final_post_it = final_pre_it - final_it_cost

    return {
        "period_log": pd.DataFrame(period_log),
        "drop_log": pd.DataFrame(drop_log),
        "warmup_period": warmup_period,
        "total_dropped": len(dropped),
        "final_n_active": final_n,
        "final_pre_it_profit": float(final_pre_it),
        "final_it_cost": float(final_it_cost),
        "final_post_it_profit": float(final_post_it),
    }


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    panel = pd.read_parquet(os.path.join(here, "data", "panel_monthly.parquet"))
    meta = pd.read_parquet(os.path.join(here, "data", "sellers_meta.parquet"))

    res = run_strategy(panel, meta)

    print("=" * 60)
    print("Strategy: one-shot drop at warmup completion")
    print("=" * 60)
    print(f"Warmup completed at:  {res['warmup_period']}")
    print(f"Total dropped:        {res['total_dropped']:,}")
    print(f"Sellers ever active:  {res['final_n_active']:,}")
    print(f"Final pre-IT profit:  {res['final_pre_it_profit']:>18,.2f}")
    print(f"Final IT cost:        {res['final_it_cost']:>18,.2f}")
    print(f"Final post-IT profit: {res['final_post_it_profit']:>18,.2f}")

    print("\nPer-period log:")
    log = res["period_log"]
    pd.set_option("display.max_rows", 30)
    pd.set_option("display.width", 200)
    pd.set_option("display.float_format", "{:,.0f}".format)
    cols = [
        "period", "n_active", "period_profit", "cum_pre_it",
        "it_cost", "cum_post_it", "warmup_done",
        "one_shot_done", "n_dropped_total",
    ]
    print(log[cols].to_string(index=False))


if __name__ == "__main__":
    main()
