# Computing the post-hoc optimal seller subset (the `y` column)

Goal: add a column `y ∈ {0, 1}` to the sellers table indicating whether each seller is kept under the post-hoc optimum. This `y` becomes the ground-truth label for downstream ML training.

## Problem formalisation

There are $N$ sellers, each with `pre_it_profit = v_i` and `quantity = q_i`. Pick a subset $S \subseteq \{1..N\}$ to maximise:

$$\Pi(S) \;=\; \sum_{i \in S} v_i \;-\; \alpha \sqrt{|S|} \;-\; \beta \sqrt{\sum_{i \in S} q_i}$$

Define binary variables $x_i = \mathbb{1}[i \in S]$. Equivalent form:

$$\max_{x \in \{0,1\}^N} \; v^T x - \alpha \sqrt{\mathbf{1}^T x} - \beta \sqrt{q^T x}$$

Brute-forcing is $2^N \approx 2^{2967}$ — infeasible. The three methods below all produce a complete `y` column.

---

## Method 1: Lagrangian fixed-point (fastest, ~ms)

### Common misunderstanding

The `keep` variable I introduced earlier is itself an **N-dimensional bool vector** — that **is** the `y` column you want. `(n_hat, I_hat)` are just convergence-tracking byproducts.

### Idea

KKT conditions tell us: at the optimum $S^*$, each seller's inclusion is decided **independently** by comparing $v_i$ against the marginal IT cost they would impose:

$$i \in S^* \quad\Longleftrightarrow\quad v_i \;>\; \underbrace{\frac{\alpha}{2\sqrt{n^*}}}_{\text{fixed marginal}} \;+\; \underbrace{\frac{\beta \cdot q_i}{2\sqrt{I^*}}}_{\text{quantity marginal}}$$

where $n^* = |S^*|$ and $I^* = \sum_{i \in S^*} q_i$.

**Intuition**: differentiate the IT cost and allocate it among sellers. Admitting one more seller costs a fixed head charge of $\alpha/(2\sqrt{n})$ (shrinking with $n$ because sqrt is concave), plus a quantity charge proportional to $q_i$. If a seller's pre-IT profit doesn't cover both, they should be kicked.

### Algorithm

Fixed-point iteration:

1. Guess an initial $(n^{(0)}, I^{(0)})$ (e.g., keep everyone)
2. Given $(n^{(t)}, I^{(t)})$, apply the threshold to every seller → get $(n^{(t+1)}, I^{(t+1)})$
3. Repeat until convergence

### Full code

```python
import numpy as np

def lagrangian_optimum(sellers, alpha=3157.27, beta=978.23, max_iter=100):
    v = sellers['pre_it_profits'].values
    q = sellers['quantity'].values

    # Initial: keep everyone
    keep = np.ones(len(sellers), dtype=bool)
    n_hat = keep.sum()
    I_hat = q[keep].sum()

    for _ in range(max_iter):
        fixed_cost = alpha / (2 * np.sqrt(max(n_hat, 1)))
        var_rate   = beta  / (2 * np.sqrt(max(I_hat, 1)))
        new_keep = v > fixed_cost + var_rate * q

        new_n = new_keep.sum()
        new_I = q[new_keep].sum()

        if (new_n, new_I) == (n_hat, I_hat):
            break
        keep, n_hat, I_hat = new_keep, new_n, new_I

    return keep   # ← N-dim bool array, this IS the y column

sellers['y_lagrangian'] = lagrangian_optimum(sellers).astype(int)
```

### Pros / cons

✅ Milliseconds to converge
✅ No external dependencies
✅ Provably the global optimum of the continuous relaxation $x \in [0, 1]^N$
⚠️ Integer optimum may differ slightly (negligible for large N in practice)

---

## Method 2: MISOCP (the second-order-cone formulation you guessed)

Your intuition was right — this is a **Mixed-Integer Second-Order Cone Program**.

### Formulation

Introduce auxiliary variables $s_n, s_I \geq 0$:

$$\begin{aligned}
\max_{x, s_n, s_I} \quad & v^T x - \alpha s_n - \beta s_I \\
\text{s.t.} \quad & s_n \geq \sqrt{\mathbf{1}^T x} \quad \text{(SOC)} \\
& s_I \geq \sqrt{q^T x} \quad \text{(SOC)} \\
& x \in \{0, 1\}^N
\end{aligned}$$

Both sqrt constraints are standard second-order cones (lower bound on a concave function → convex constraint). The integer variable promotes it from SOCP to MISOCP.

### CVXPY implementation

```python
import cvxpy as cp

def misocp_optimum(sellers, alpha=3157.27, beta=978.23):
    N = len(sellers)
    v = sellers['pre_it_profits'].values
    q = sellers['quantity'].values

    x  = cp.Variable(N, boolean=True)
    sn = cp.Variable(nonneg=True)
    sI = cp.Variable(nonneg=True)

    obj = cp.Maximize(v @ x - alpha * sn - beta * sI)
    constraints = [
        sn >= cp.sqrt(cp.sum(x)),
        sI >= cp.sqrt(q @ x),
    ]
    prob = cp.Problem(obj, constraints)
    prob.solve(solver=cp.MOSEK)   # or cp.GUROBI / cp.SCIP
    return x.value > 0.5

sellers['y_misocp'] = misocp_optimum(sellers).astype(int)
```

### Pros / cons

✅ **Strictly integer optimal** (not a continuous relaxation)
✅ Can be used as ground truth to validate the Lagrangian method
⚠️ Requires a MIP-capable SOCP solver: MOSEK / Gurobi (commercial), SCIP (open source but slow)
⚠️ The integer problem at N=2967 takes MOSEK a few minutes to tens of minutes
⚠️ Open-source ECOS_BB may time out at this N

### Practical advice

Verify agreement on a small subsample first, then scale up:

```python
# Take 200 sellers as a sandbox
sample = sellers.sample(200, random_state=0).reset_index(drop=True)
y_lag  = lagrangian_optimum(sample)
y_soc  = misocp_optimum(sample)
print("agreement:", (y_lag == y_soc).mean())   # should be > 0.98
```

If agreement is high, the Lagrangian method is enough on this data — use it on the full set. If they diverge, bite the bullet and run the full MISOCP.

---

## Method 3: local-search post-processing (tighten the last screws)

Whatever method gives the initial solution $x^{(0)}$, you can polish off any integer gap with a local swap pass:

```python
def local_swap_refine(keep, sellers, alpha=3157.27, beta=978.23):
    v, q = sellers['pre_it_profits'].values, sellers['quantity'].values

    def profit(mask):
        n = mask.sum(); I = q[mask].sum()
        if n == 0: return 0.0
        return v[mask].sum() - alpha*np.sqrt(n) - beta*np.sqrt(I)

    keep = keep.copy()
    improved = True
    while improved:
        improved = False
        cur = profit(keep)
        # Single-bit flips
        for i in range(len(keep)):
            keep[i] = not keep[i]
            if profit(keep) > cur + 1e-6:
                cur = profit(keep); improved = True
            else:
                keep[i] = not keep[i]
    return keep

sellers['y'] = local_swap_refine(lagrangian_optimum(sellers), sellers).astype(int)
```

Each pass is O(N) flips; usually stabilises in 1-2 passes.

---

## Recommended final pipeline

```python
# 1) Lagrangian for the initial solution (milliseconds)
keep_lag = lagrangian_optimum(sellers)

# 2) Single-bit flips to refine (seconds)
keep_final = local_swap_refine(keep_lag, sellers)

# 3) This is your y column
sellers['y'] = keep_final.astype(int)

# 4) (Optional) MISOCP verification on a sample
# ... see sandbox code above
```

These three steps together produce a near-optimal `y` column for downstream ML labels.

---

## Next: train a predictive model on `y`

With `y` in hand, each seller has one row:

| feature | source |
|---|---|
| `delay_to_carrier` | `Seller.get_training_data` |
| `wait_time` | same |
| `quantity_per_order` | same |
| `share_of_one_stars` | same |
| `seller_state` | one-hot |
| ... | other features not dependent on future revenue |
| **`y`** | **0/1 from Lagrangian + local swap** |

⚠️ Key constraint: features must not include `pre_it_profits / sales / review_cost / months_on_olist` — these are **post-hoc summaries**. Including them would make the model "predict outcome from outcome". Use only features observable at onboarding or in the first N months, so the trained classifier can score newly onboarded sellers.

Minimal viable model:

```python
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score

X = sellers[features_no_leakage]
y = sellers['y']

model = LogisticRegression(class_weight='balanced')
print(cross_val_score(model, X, y, cv=5, scoring='roc_auc'))
```

Compare this ML strategy against baseline strategies (honeymoon + threshold, etc.) on regret/gap as outlined in `research_ideas.md`.
