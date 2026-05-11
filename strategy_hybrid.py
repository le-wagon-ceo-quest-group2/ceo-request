"""Strategy C (hybrid): warmup + first-batch one-shot + ongoing 3rd-month drops.

  Phase 1 (warmup):       no drops while cum_post_it_profit <= 0.
  Phase 2 (first batch):  in the first period after warmup completes,
                          evaluate every seller with >= 2 months of history
                          (i.e., onboarded at least 2 months before).
                          Apply the closed-form strong-drop test.
  Phase 3 (ongoing):      each subsequent month, evaluate any seller whose
                          3rd active month is THIS period (same as Strategy A).

Forward-only realised P&L accounting.
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

    onboard_map = dict(zip(meta.seller_id, meta.onboard_period))

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
    first_batch_done = False
    first_batch_drop_count = 0

    for t in periods:
        new_drops: set = set()

        if warmup_done:
            if not first_batch_done:
                # ---- Phase 2: one-shot batch eval, sellers with >= 2 months ----
                history = panel[panel.period < t]
                grouped = history.groupby("seller_id").agg(
                    v_obs_sales=("sales_t", "sum"),
                    v_obs_sub=("sub_fee_t", "sum"),
                    v_obs_review=("review_cost_t", "sum"),
                    q_obs=("n_items_t", "sum"),
                    history_months=("period", "size"),
                )
                grouped["v_obs"] = (
                    grouped.v_obs_sales * 0.10
                    + grouped.v_obs_sub
                    - grouped.v_obs_review
                )
                eligible = grouped[grouped.history_months >= 2]
                if cum_n >= 2 and cum_q > 0 and len(eligible) > 0:
                    qi = eligible["q_obs"].values
                    valid = qi < cum_q
                    fixed_marg = alpha * (np.sqrt(cum_n) - np.sqrt(cum_n - 1))
                    var_marg = np.where(
                        valid,
                        beta * (
                            np.sqrt(cum_q) - np.sqrt(np.maximum(cum_q - qi, 0.0))
                        ),
                        np.inf,
                    )
                    threshold = fixed_marg + var_marg
                    mask = (eligible["v_obs"].values < threshold) & valid
                    new_drops = set(eligible.index[mask])
                first_batch_done = True
                first_batch_drop_count = len(new_drops)
            else:
                # ---- Phase 3: ongoing 3rd-month evaluation (Strategy A logic) ----
                present_at_t = panel.loc[panel.period == t, "seller_id"].unique()
                for sid in present_at_t:
                    if sid in dropped:
                        continue
                    ob = onboard_map[sid]
                    if (t - ob).n != 2:
                        continue
                    history = panel[
                        (panel.seller_id == sid) & (panel.period < t)
                    ]
                    if len(history) < 2:
                        continue
                    v_obs = (
                        history.sales_t.sum() * 0.10
                        + history.sub_fee_t.sum()
                        - history.review_cost_t.sum()
                    )
                    q_obs = history.n_items_t.sum()
                    if cum_n < 2 or cum_q <= q_obs:
                        continue
                    threshold = (
                        alpha * (np.sqrt(cum_n) - np.sqrt(cum_n - 1))
                        + beta * (np.sqrt(cum_q) - np.sqrt(cum_q - q_obs))
                    )
                    if v_obs < threshold:
                        new_drops.add(sid)

        dropped |= new_drops
        for sid in new_drops:
            drop_log.append({"period_dropped": t, "seller_id": sid})

        # Period P&L
        active_t = panel[
            (panel.period == t) & (~panel.seller_id.isin(dropped))
        ]
        period_profit = (
            active_t.sales_t.sum() * 0.10
            + active_t.sub_fee_t.sum()
            - active_t.review_cost_t.sum()
        )
        cum_pre_it += period_profit

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
            "first_batch_done": first_batch_done,
            "n_dropped_this_period": len(new_drops),
            "n_dropped_total": len(dropped),
        })

    # Forward-only final accounting
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
        "first_batch_dropped": first_batch_drop_count,
        "ongoing_dropped": len(dropped) - first_batch_drop_count,
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
    print("Strategy C: hybrid (first-batch one-shot + ongoing 3rd-month)")
    print("=" * 60)
    print(f"Warmup completed at:  {res['warmup_period']}")
    print(f"First-batch dropped:  {res['first_batch_dropped']:,}")
    print(f"Ongoing dropped:      {res['ongoing_dropped']:,}")
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
        "first_batch_done", "n_dropped_this_period", "n_dropped_total",
    ]
    print(log[cols].to_string(index=False))


if __name__ == "__main__":
    main()