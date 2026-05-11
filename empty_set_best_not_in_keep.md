# The best seller at the empty platform is not guaranteed to be in the keep set

## The question

Let $i^* = \arg\max_i \Delta_i(\emptyset)$ — "the seller whose marginal loss (or gain) is smallest when added to an empty platform".

Is $i^*$ guaranteed to belong to some global optimum $S^*$?

## Answer: two cases

### Case 1: $\Delta_{i^*}(\emptyset) > 0$ → yes, always in

$i^*$ trivially passes the closed-form strong-keep test $v_i > \alpha + \beta \sqrt{q_i}$. It belongs to $\mathcal{K}^{++}$ and therefore appears in **every** global optimum.

### Case 2: $\Delta_{i^*}(\emptyset) \leq 0$ (Olist's actual situation) → **not necessarily**

This is exactly the propagation-K=0 scenario — every seller has $\Delta(\emptyset) \leq 0$, yet non-empty optima still exist.

Intuitively, "not profitable alone but profitable inside a healthy crowd" sounds reasonable, **but a counterexample can be constructed**.

## Counterexample

Parameters: $\alpha = 100$, $\beta = 10$.

| seller | v | q | $\Delta(\emptyset)$ |
|---|---|---|---|
| $i^*$ | 4 | 1 | $4 - 100 - 10\sqrt{1} = -106$ |
| $j_1, \ldots, j_{100}$ (100 sellers) | 70 | 100 | $70 - 100 - 10\sqrt{100} = -130$ |

$i^*$ ranks highest under the empty-set criterion ($-106 > -130$).

### Test: add $i^*$ to $S = \{j_1, \ldots, j_{100}\}$

Compute $\Pi(S)$:

$$\Pi(S) = 70 \cdot 100 - 100\sqrt{100} - 10\sqrt{10000} = 7000 - 1000 - 1000 = 5000$$

Now the marginal $\Delta_{i^*}(S)$ of adding $i^*$:

- IT fixed marginal: $100(\sqrt{101} - \sqrt{100}) \approx 4.98$
- IT items marginal: $10(\sqrt{10001} - \sqrt{10000}) \approx 0.05$
- Total cost $\approx 5.03$

$$\Delta_{i^*}(S) = v_{i^*} - 5.03 = 4 - 5.03 = -1.03 < 0$$

**Conclusion**: adding $i^*$ to $S$ reduces profit by 1.03 BRL. So the optimum is $S$ itself, and **$i^*$ is not in the optimum** — even though $i^*$ is "best" under the empty-set criterion.

## Why this happens: two orderings flip across $S$

### Empty-set regime

When $S = \emptyset$, every seller pays the full startup cost $\alpha + \beta\sqrt{q_i}$, so **low-$q$ sellers have a major advantage** (the $\sqrt{q_i}$ term is small).

The ordering is dominated by $v_i - \beta\sqrt{q_i}$. Although $i^*$ has low $v$, its $\sqrt{q}$ is also low, beating $j$.

### Large-platform regime

When $|S|$ is large and $Q_S$ is large:

$$\Delta_i(S) \approx v_i - \frac{\beta q_i}{2\sqrt{Q_S}}$$

The second term is crushed by $\sqrt{Q_S}$ and approaches 0. **The ordering is essentially determined by $v_i$.**

Here $j$ ($v=70$) crushes $i^*$ ($v=4$).

### The two orderings can completely reverse

- Empty: $i^* \succ j$
- Large platform: $j \succ i^*$

In our counterexample, the optimum sits in the "large platform" regime, so it contains only the $j$ sellers and excludes $i^*$.

## Mathematical core

Two simplified ranking keys:

| Ranking key | Applies when | Expression |
|---|---|---|
| Startup-era ranking | $S \approx \emptyset$ | $v_i - \beta\sqrt{q_i}$ |
| Steady-state ranking | $|S|$ and $Q_S$ are large | $v_i$ (leading term) or $v_i / q_i$ (lower-order term) |

Explicitly for a given $S$:

$$\Delta_i(S) - \Delta_j(S) = (v_i - v_j) - \beta\bigl(\sqrt{Q_S + q_i} - \sqrt{Q_S + q_j}\bigr)$$

The second term varies monotonically with $Q_S$. If $q_i \ne q_j$ and $v_i \ne v_j$, the sign of this difference can **flip as $Q_S$ changes** — the ordering itself flips.

The flip point lies at some critical $Q_S^*$. Which side of this point the optimum's $Q_{S^*}$ falls on determines the relative ordering of $i$ and $j$.

## Operational consequences

When all sellers satisfy $\Delta_i(\emptyset) \leq 0$:

| Proposition | Truth |
|---|---|
| All sellers in the optimum satisfy $\Delta(\emptyset) \leq 0$ | ✅ trivially under the premise |
| All sellers in the optimum satisfy $\Delta(S^* \setminus \{i\}) > 0$ | ✅ by definition of optimum |
| **The seller with the largest $\Delta(\emptyset)$ is in the optimum** | ❌ **counterexample above** |
| The seller with the largest $\Delta$ on a large platform is in the optimum | ❌ also not guaranteed |

**There is no simple "rank by $\Delta(\emptyset)$" heuristic that recovers the optimum directly.** This is precisely why, when propagation gives K=0, we cannot just "promote the top-$\Delta(\emptyset)$ sellers into K" — they might not appear in any global optimum at all.

## Vindication of the Lagrangian approach

The Lagrangian fixed-point threshold

$$\tau_i = \frac{\alpha}{2\sqrt{n^*}} + \frac{\beta q_i}{2\sqrt{I^*}}$$

is the **converged marginal cost**, not the initial cost at the empty platform. The KKT conditions capture the true marginal "after the platform has reached steady state", so the resulting ordering reflects the relative strength of sellers under the *optimal* environment. The $\Delta(\emptyset)$ ordering, as the counterexample shows, is misleading.

This also explains: **propagation stopping at K=0 isn't laziness — it's that, under the weakened definition, genuinely no seller is "profitable in every environment".**

To go further we must use methods like Lagrangian + MISOCP sensitivity that judge sellers under the **true optimal environment**, not the empty-platform extreme.

## Implications for ML labelling

**Do not** use the following heuristic for labelling sellers as "keep":

```python
# ❌ wrong heuristic
delta_empty = v - alpha - beta * np.sqrt(q)
y_naive = (delta_empty > some_threshold).astype(int)
```

This mislabels "high $v$, high $q$" sellers (often the backbone of the optimum) as 0.

The **correct** sources of heuristic labels, in decreasing confidence:

1. Propagation's D: **100% reliable** $y = 0$
2. Propagation's K: **100% reliable** $y = 1$ (empty for our dataset)
3. Lagrangian's keep: **strong candidate** $y = 1$ (effectively ground truth when it agrees with propagation)
4. MISOCP no-good-cut verified unique optimum: **true ground truth**
