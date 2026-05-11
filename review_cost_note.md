# Why `cost_map[round(avg(score))] * n_reviews` is wrong

## The proposal

A teammate suggested computing each seller's review cost as:

```python
review_cost = cost_map[round(avg(review_score))] * num_of_reviews
```

where `cost_map = {1: 100, 2: 50, 3: 40, 4: 0, 5: 0}` (BRL per bad review).

This looks reasonable, but is **systematically wrong** for any seller whose reviews aren't all the same score. Below is why.

## What the spec actually says

From the P&L rules:

> _Estimated reputation costs of orders with bad reviews (≤ 3 stars). We make an assumption about the monetary cost **for each bad review**._

The cost is defined **per review**. The correct formula is therefore a sum over reviews:

```
cost(seller) = Σ cost_map[score_i]   for each review i associated with that seller
```

Equivalently, if `n_s` is the number of the seller's reviews with score `s`:

```
cost(seller) = Σ n_s · cost_map[s]
```

## Why the proposal is not equivalent

Let `p(s)` be the share of the seller's reviews having score `s`. The correct expected cost per review is:

```
E[cost] = Σ p(s) · cost_map[s]
```

The proposal computes:

```
cost_map[round(E[s])]
```

These two quantities are equal **only if `cost_map` is linear in `s`** — but `cost_map` is **non-linear, non-monotonic, and discontinuous**:

| score | cost |
|------:|-----:|
| 1     | 100  |
| 2     |  50  |
| 3     |  40  |
| 4     |   0  |
| 5     |   0  |

The cost drops from 40 → 0 between score 3 and 4, jumps unevenly elsewhere, and is flat from 4 onward. There is no way `cost_map[round(avg))]` recovers the true sum except in the degenerate case where every review has the same score.

## Concrete counter-examples

All three sellers below have 100 reviews:

| seller | 1-star | 5-star | avg  | round(avg) | proposed cost     | true cost            | error    |
|-------:|-------:|-------:|-----:|-----------:|------------------:|---------------------:|---------:|
| A      |    5   |   95   | 4.80 |     5      | 0 × 100 = **0**   | 5 × 100 = **500**    | **−500** |
| C      |   50   |   50   | 3.00 |     3      | 40 × 100 = **4000** | 50 × 100 = **5000** | **−1000** |
| D      |   30   |   70   | 3.80 |     4      | 0 × 100 = **0**   | 30 × 100 = **3000**  | **−3000** |

**Pattern:** the proposal *under-estimates* whenever a seller mixes good and bad reviews — and the more good reviews dilute the average, the worse the under-estimate gets.

## The rounding cliff

Even setting aside non-linearity, `round()` introduces a discontinuity with no business basis:

- `round(3.49) = 3` → cost per review = 40
- `round(3.50) = 4` → cost per review = 0

A seller whose average shifts by 0.01 sees their attributed cost change by 40 BRL × N reviews. There is nothing in the problem statement that supports such a cliff.

## Why this matters for the analysis

`profits = revenue − review_cost` feeds directly into the what-if analysis:

1. We sort sellers by `profits` descending.
2. We `cumsum` profits.
3. We pick the cut-off via `argmax`.

If `review_cost` is systematically under-estimated for high-volume sellers with mixed reviews, those sellers will appear *more profitable than they really are*. The `argmax` lands on the wrong cut-off, and the recommendation to the CEO is biased toward keeping sellers Olist should have removed.

## The correct approach

The TA-confirmed rule is:

1. **Per order**, take the most recent review (`review_creation_date`).
2. Look up its cost via `cost_map`.
3. Attribute the **full** cost to **every seller** involved in that order (no splitting).
4. Sum per `seller_id`.

```python
latest_review = (order_reviews
                 .sort_values('review_creation_date')
                 .groupby('order_id', as_index=False)
                 .tail(1)[['order_id', 'review_score']])

oi_dedup = order_items[['order_id', 'seller_id']].drop_duplicates()

x = oi_dedup.merge(latest_review, on='order_id')
x['review_cost'] = x['review_score'].map(cost_map)

review_cost_per_seller = x.groupby('seller_id')['review_cost'].sum()
```

This is per-review summation by construction, so it is correct for any review-score distribution.

## If the teammate really wants a "vectorised at seller level" form

The proposal *can* be salvaged by replacing the rounding step with an actual expectation:

```python
# rows = sellers, columns = score 1..5, values = count of reviews
counts = reviews_per_seller_score                  # shape (n_sellers, 5)
review_cost = counts.mul(pd.Series(cost_map), axis=1).sum(axis=1)
```

This is mathematically identical to per-review summation but stays at seller granularity, which may be the ergonomic appeal of the original idea. The key is that **the cost lookup has to happen before any aggregation over scores**, never after.
