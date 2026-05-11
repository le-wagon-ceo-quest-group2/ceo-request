# Olist Seller Selection — from hindsight analysis to online strategy

## Starting point

The current `CEO_request` analysis has two problems:

1. **It uses future information**: deciding to "drop a seller" presupposes knowledge of their entire historical performance. Olist cannot know this at onboarding time.
2. **Even allowing hindsight**, "sort by pre-IT profit + argmax cumulative" is **not the optimum**. There is no theorem saying this greedy procedure maximises post-IT profit.

A more robust research framework is three-tiered:

```
Theoretical upper bound (clairvoyant optimum)
        ↑
   Strategy P's actual return
        ↑
   Benchmark (current pre-IT sort method)
```

| Quantity | Meaning |
|---|---|
| Π_optimal   | True post-hoc optimum (upper bound) |
| Π_benchmark | Current pre-IT sort + argmax |
| Π_P         | Real profit of strategy P decided online |
| regret_P    | Π_optimal − Π_P |
| gap_P       | Π_P − Π_benchmark |

---

## 1️⃣ First, prove pre-IT sort is not optimal

No need for an extreme constructed counterexample — just run a **local swap**:

```python
S = set(sellers_exp1.iloc[:n_keep].index)
removed = set(sellers_exp1.iloc[n_keep:].index)

def profit(S):
    n = len(S)
    items = sellers.loc[list(S), 'quantity'].sum()
    return sellers.loc[list(S), 'pre_it_profits'].sum() - it_cost(n, items)

best_swap = None
for i in S:
    for j in removed:
        new = (S - {i}) | {j}
        if profit(new) > profit(S):
            best_swap = (i, j, profit(new) - profit(S))
            break
```

- O(N²) ≈ 9M evaluations, finishes in minutes
- Finding any single swap that improves profit proves the current method is suboptimal
- Make it a demo in the notebook: one red line "current method leaves +X BRL on the table" tells the CEO why this matters

---

## 2️⃣ Push to the upper bound: Lagrangian fixed-point

Brute-force $2^{2967}$ is impossible. But the objective function has a very pretty structure:

$$\max_{S} \sum_{i \in S} v_i - \alpha\sqrt{n_S} - \beta\sqrt{I_S}$$

KKT conditions give a **characterisation of the optimum**: seller $i$ is in the optimal set ⇔

$$v_i > \underbrace{\frac{\alpha}{2\sqrt{n^*}}}_{\text{fixed marginal cost}} + \underbrace{\frac{\beta \cdot q_i}{2\sqrt{I^*}}}_{\text{per-item marginal cost}}$$

In other words: **given** $(n^*, I^*)$, each seller's inclusion is an **independent decision** — filter by a threshold linked to their quantity.

This reduces the $2^N$ combinatorial search to a fixed-point search in the 2D $(n, I)$ space:

```python
def lagrangian_step(n_hat, I_hat):
    fixed_cost = alpha / (2 * np.sqrt(max(n_hat, 1)))
    var_rate   = beta  / (2 * np.sqrt(max(I_hat, 1)))
    keep = sellers['pre_it_profits'] > fixed_cost + var_rate * sellers['quantity']
    return keep.sum(), sellers.loc[keep, 'quantity'].sum(), keep

n_hat, I_hat = sellers_exp1.shape[0], sellers['quantity'].sum()
for _ in range(50):
    n_new, I_new, keep = lagrangian_step(n_hat, I_hat)
    if (n_new, I_new) == (n_hat, I_hat):
        break
    n_hat, I_hat = n_new, I_new
```

- Typically converges in < 20 iterations
- Concave objective ⇒ KKT optimum (in the continuous-relaxation sense)
- Integer optimum may deviate slightly; for large N the gap is tiny
- Rigorous variant: follow up with the step-1 local swap as post-processing

---

## 3️⃣ Online strategies with no future information

Slice the data by time (monthly), and at each time t decide:

> Given the data observed up to time t, which sellers should be removed?

### A. Bayesian screening

Treat each seller's review score as a sample from an unknown distribution. Use a Beta-Binomial / Dirichlet conjugate to estimate the posterior of "the seller's true 1-star probability ≥ threshold"; cut if the posterior credibility is above 95%.

- ✅ Naturally handles "we can't conclude anything from one order"
- Knobs: cut threshold + credibility

### B. Rolling-window inflection method

Each month, take the last 3 months' data; compute marginal profit at the current IT cost. If marginal < 0 for 2 consecutive months, cut.

- ✅ Simple, no distributional assumptions
- ⚠️ Sensitive to review noise

### C. Honeymoon period + threshold (mentioned in cell-24 of the task)

Don't touch new sellers for N months; then if cumulative marginal profit < threshold, cut.

- ✅ Easy to implement and communicate
- A univariate baseline to compare against A/B

### D. Multi-armed bandit

Each seller is an arm. Thompson sampling estimates mean reward; variance drives exploration.

### E. Quality classifier

Use first-6-month features (delay_to_carrier, early review distribution, quantity_per_order…) to predict 12-month marginal profit. LR / GBT both work. Pick the decision threshold that maximises expected profit.

- ✅ Easiest to productionise, most "ML-system-like"
- Good for a product-grade demo

---

## 4️⃣ Evaluation pipeline

| Output | How to compute |
|---|---|
| Upper bound Π_optimal | Lagrangian fixed-point from §2 |
| Benchmark Π_benchmark | Existing sort-by-pre_IT + argmax |
| Strategy Π_P | Replay data through time and simulate P's online decisions |

Visualisations:

- Bar chart of regret / gap for 5 strategies
- Cumulative profit vs time, one line per strategy
- Shade the band [Π_benchmark, Π_optimal]; all strategies live inside it

---

## 5️⃣ Prioritisation

For a full study, work in this order:

| Stage | Duration | Output |
|---|---|---|
| 1 | 2 days | Upper bound (Lagrangian) + benchmark gap, plot |
| 2 | 3 days | Implement strategies C and E |
| 3 | 2 days | Replay data at t = 6 / 12 / 18 months and run all strategies |
| 4 | 1 day | Write report + regret time-series plot |

If you only want to verify the critique: **do stage 1**, half a day gives the answer:

- gap < 1% → status quo is acceptable
- gap > 5% → worth continuing the study

---

## Methodological note

This framework is essentially **counterfactual policy evaluation**: separate policy evaluation from the oracle upper bound. It's the dominant pattern in RL / recommender systems / personalised pricing.

Olist's special advantage is that **the objective has structure** (concave), so the upper bound is **tractable** (Lagrangian method) — no need for brute-force Monte Carlo as in general settings. This is a great topic for a paper / blog post / capstone.
