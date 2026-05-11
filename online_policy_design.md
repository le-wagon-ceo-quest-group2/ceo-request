# Online-strategy framework design

## Overall goal

Slice Olist's data by time period. At each period, simulate a decision; **each decision is allowed to use only the data observed before that period**. Then compare each strategy's cumulative profit against the upper bound (Lagrangian post-hoc optimum) and the baseline (keep_all).

## 1. Period granularity

**Choose monthly** — reasons:

- Subscription fee is billed monthly (80 BRL/month), a natural time unit
- Review feedback cycle is ~1–2 weeks; monthly granularity accumulates enough signal
- Olist's data spans ~24 months (2016-09 to 2018-09) — plenty for backtest, not too fine

Slicing monthly gives roughly 24 periods over the full dataset.

## 2. Data restructuring

Convert the raw `orders`, `order_items`, `order_reviews` into a **(seller_id, period_t)** long table:

| Field | Source | Meaning |
|---|---|---|
| `seller_id` | – | Primary key 1 |
| `period` | Month of `order_purchase_timestamp` | Primary key 2 |
| `n_orders_t` | count | Seller's orders in this month |
| `n_items_t` | count | Seller's items in this month |
| `sales_t` | sum(price) | Sales revenue this month |
| `n_reviews_t` | count | Reviews received this month |
| `n_one_star_t` | sum(score==1) | 1-star count |
| `n_two_star_t` | … | … |
| `n_five_star_t` | … | … |
| `is_active_t` | bool | Was the seller active this month (onboarded, not yet dropped) |

**Onboarding time**: the seller's first order month.

**Review attribution time**: the `review_creation_date` month (not the order month), since review cost is incurred at score generation.

## 3. Strategy interface

```python
class Policy:
    """Each strategy implements this interface."""

    def decide(self, history: pd.DataFrame, period: int) -> set[str]:
        """
        history: long table of all (seller_id, period') rows with period' < period —
                 i.e., what the strategy can see at the start of `period`
        period:  the current decision period
        return:  the set of seller_ids newly dropped this period
                 (don't re-emit already-dropped sellers)
        """
```

The strategy outputs the new drops; the simulator maintains `dropped_so_far` cumulatively. Once dropped, a seller contributes no further sales / reviews / IT cost.

## 4. Simulator structure

```python
def backtest(policy: Policy, panel: pd.DataFrame,
             alpha=ALPHA, beta=BETA) -> dict:
    """
    panel: full long table (seller_id, period, n_orders_t, ..., n_five_star_t)
    return: {
        'profits_by_period': pd.Series,
        'cum_profit': pd.Series,
        'final_post_it_profit': float,
        'dropped_per_period': dict[period -> set],
        'kept_at_end': set,
    }
    """
    dropped = set()
    profits = []

    for t in sorted(panel.period.unique()):
        # 1. Strategy decides based on history (period < t)
        history = panel[(panel.period < t) & (~panel.seller_id.isin(dropped))]
        new_drops = policy.decide(history, t)
        dropped |= new_drops

        # 2. Period profit counts only non-dropped sellers
        active = panel[(panel.period == t) & (~panel.seller_id.isin(dropped))]
        sales_fee_t = active.sales_t.sum() * 0.10
        sub_fee_t = active.seller_id.nunique() * 80      # active sellers × 80
        review_cost_t = sum(active[col].sum() * cost for col, cost in [
            ('n_one_star_t', 100), ('n_two_star_t', 50), ('n_three_star_t', 40)
        ])
        profits.append({
            'period': t,
            'sales_fee': sales_fee_t,
            'sub_fee': sub_fee_t,
            'review_cost': review_cost_t,
            'period_profit': sales_fee_t + sub_fee_t - review_cost_t,
        })

    df_profits = pd.DataFrame(profits).set_index('period')

    # 3. IT cost is "cumulative over all retained sellers / items"
    kept_at_end = panel[~panel.seller_id.isin(dropped)]
    n_total = kept_at_end.seller_id.nunique()
    q_total = kept_at_end.n_items_t.sum()
    it_cost_total = alpha * np.sqrt(n_total) + beta * np.sqrt(q_total)

    pre_it = df_profits.period_profit.sum()
    post_it = pre_it - it_cost_total

    return {
        'profits_by_period': df_profits.period_profit,
        'cum_profit': df_profits.period_profit.cumsum(),
        'pre_it_profit': pre_it,
        'it_cost_total': it_cost_total,
        'final_post_it_profit': post_it,
        'kept_at_end': set(panel.seller_id.unique()) - dropped,
    }
```

## 5. Key counterfactual semantics

⚠️ A few **must-state** assumptions, without which the comparison is meaningless:

1. **Customer behaviour is exogenous**: dropping a seller only removes that seller's orders/items/reviews; there is no "buyer switches to a different seller" substitution effect. A simplification, but a reasonable one.

2. **IT cost is summed once at the end**: the original problem's IT cost is sqrt(cumulative), not sqrt(per-month). Compute IT cost once at the end of the simulation; do not add it to each period.

3. **Drops are irreversible**: once a strategy drops a seller, no later period can resurrect them. To allow "stop then restart", the interface needs extension.

4. **Subscription fee is monthly while online**: 80 BRL is owed each month the seller is online; once dropped, it stops. Consistent with the original "months_on_olist × 80" formula (a dropped seller's months are fewer than a kept one's).

5. **Review cost timing**: a review's cost is incurred in the month it is generated, not the month of the corresponding order. Otherwise we'd have ambiguity like "order in t1, review in t2, drop happened in between — does this cost still apply?". The "review-creation month" convention is the cleanest.

## 6. First batch of strategies to test (increasing complexity)

### Baselines

| Name | Description |
|---|---|
| `keep_all` | Never drop. Pure baseline. |
| `oracle_clairvoyant` | Use the Lagrangian post-hoc solution and drop everyone "marked for drop" at the start. This is the upper bound. |

### Simple heuristics

| Name | Description | Knobs |
|---|---|---|
| `drop_after_first_one_star` | Drop on the very first 1-star review | none |
| `drop_if_k_bad_in_window` | Drop if rolling N-month window has ≥ K reviews of ≤ 3 stars | N, K |
| `honeymoon_threshold` | Don't touch a seller for H months; afterwards, if cumulative marginal profit < threshold, drop | H, threshold |

### Model-based strategies

| Name | Description |
|---|---|
| `bayesian_review` | Beta-Binomial posterior on the seller's true 1-star rate; drop if credibility ≥ 95% exceeds threshold |
| `rolling_marginal` | Each month, compute marginal profit over the last K months (using current IT marginal); drop if < 0 for M consecutive months |
| `ml_classifier` | Train a classifier on first-H-months features predicting later marginal profit; decide by threshold on predicted value |

## 7. Evaluation output

For each strategy, record:

- `final_post_it_profit` (the core metric)
- `kept_at_end` size
- Cumulative-profit time series per period (for plotting)
- regret = `Π_oracle - Π_strategy`
- gap = `Π_strategy - Π_baseline`

Aggregated table:

| Strategy | post-IT profit | regret | gap | Kept | Time-series signature |
|---|---|---|---|---|---|
| keep_all | – | (large) | 0 | 2967 | Stable but low |
| oracle | (max) | 0 | (large) | ~2117 | Not realistic; reference line |
| drop_after_first_one_star | ? | ? | ? | ? | Early steep drop? |
| … | | | | | |

## 8. Implementation stages

In this order:

1. **Stage 1 (data side)**: write `build_panel(orders, items, reviews) -> long_df`, then sanity-check:
   - Total sales, total quantity, total review_cost match the raw data
   - panel.shape ≈ 2967 sellers × ~24 periods (not every seller covers all periods, but aggregates match)

2. **Stage 2 (simulator)**: implement `backtest(policy, panel)`. Validate with `keep_all` — its output should equal the full-platform P&L from `Seller.get_training_data()`.

3. **Stage 3 (reference strategies)**: run `oracle_clairvoyant` for the upper bound and `keep_all` for the lower; establish the comparison axes.

4. **Stage 4 (heuristics)**: add the three simple heuristics in turn, plot each.

5. **Stage 5 (model-based)**: Bayesian / rolling / classifier strategies, each compared against baseline + oracle.

6. **Stage 6 (sensitivity)**: grid-search knobs of each strategy; plot regret vs knob value.

## 9. Possible pitfalls

1. **Cold-start periods**: early months have very few orders (only dozens in 2016-09 / 10), so any strategy's judgement is unreliable. Mark this region separately in plots.

2. **Sellers who don't drop but become inactive**: a seller may place 1–2 orders one month then disappear. Is that "natural churn"? Suggestion: only count rows that actually appear in the panel; don't pad zero rows per seller — the simulator cares about *active* drops only.

3. **Decision timing within a period**: "based on data before this period" strictly means "at the start of the period". If a strategy wants to see the current period's reviews, be explicit. The realistic case is a 1-period review lag.

4. **Sellers with 0 orders in the current period**: dropping doesn't change the period's profit (they contributed nothing), but their subscription stops. The simulator must handle the "online but no sales" state.

5. **Oracle ≠ Lagrangian.keep directly**: Lagrangian gives the "end-of-horizon" optimal drop list; in a time-series simulation, *when* you drop also matters (early drops save subscription but lose sales fees). The ideal oracle decides "should we accept seller s the first time they appear?" — a finer optimisation. A simplification: drop a seller at the end of their first period if they're in Lagrangian.drop.

## 10. Open design questions

To resolve before implementation:

1. **Decision timing inside a period**: does the strategy's history include all of period t-1's reviews, or is there a 1-period lag?
2. **Initial observation window for new onboards**: can the strategy drop a seller on their first appearance, or must it wait for at least 1 review?
3. **Feature engineering**: does the strategy only see the raw panel, or can it compute derived features like "average wait_time over the last 3 months"? Suggestion: allow derived features, but only computed on the history slice (no future leakage).
4. **Training window for ML strategies**: full history vs rolling window? Full → more data but distribution drift; rolling → drift-resistant but less data.

---

Once this framework is fixed, the rest is engineering.

Shall I start by implementing **Stage 1 (data restructuring)**? It's the most critical and bug-prone step; everything downstream uses the panel long table as input.
