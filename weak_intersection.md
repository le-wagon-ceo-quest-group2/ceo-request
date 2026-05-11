# Weakened version: unconditionally-profitable / unconditionally-unprofitable sellers

## Restating the question

Your weakening defines two sets:

| Set | Definition | Meaning |
|---|---|---|
| **Strong must-keep** $\mathcal{K}^{++}$ | $\{i : \Delta_i(S) > 0 \;\forall\; S \subseteq \{1..N\} \setminus \{i\}\}$ | For **any** subset of existing sellers, adding $i$ increases profit |
| **Strong must-drop** $\mathcal{D}^{++}$ | $\{i : \Delta_i(S) < 0 \;\forall\; S \subseteq \{1..N\} \setminus \{i\}\}$ | For **any** subset of existing sellers, adding $i$ decreases profit |

where $\Delta_i(S) = \Pi(S \cup \{i\}) - \Pi(S)$ is seller $i$'s marginal contribution.

## Relationship to the original problem

**Proposition 1**: $\mathcal{K}^{++} \subseteq \mathcal{K}$ (strong must-keep ⊂ must-keep across optima)

Proof: if $i \in \mathcal{K}^{++}$, then for any $S^* \in \mathcal{S}^*$ with $i \notin S^*$, $\Delta_i(S^* \setminus \{i\}) > 0$, hence $\Pi(S^* \cup \{i\}) > \Pi(S^*) = \Pi^*$, a contradiction. $\square$

**Proposition 2**: $\mathcal{D}^{++} \subseteq \mathcal{D}$ (analogously)

So this is **genuinely a weakening** — $\mathcal{K}^{++}, \mathcal{D}^{++}$ are strict subsets (or equal to) the true intersection, but absolutely correct (sound).

## Key observation: marginal cost is monotone

For our objective function:

$$\Delta_i(S) \;=\; v_i \;-\; \underbrace{\alpha (\sqrt{|S|+1} - \sqrt{|S|})}_{\text{IT fixed marginal}} \;-\; \underbrace{\beta (\sqrt{Q_S + q_i} - \sqrt{Q_S})}_{\text{IT quantity marginal}}$$

Both IT marginal terms are **monotonically decreasing** in $|S|$ and $Q_S$ (since sqrt is concave). So:

$$\Delta_i(\emptyset) \;\leq\; \Delta_i(S) \;\leq\; \Delta_i(\{1..N\} \setminus \{i\})$$

That is:

- At **empty set**, IT marginal cost is maximal → $\Delta_i$ is minimal
- At **near-full set**, IT marginal cost is minimal → $\Delta_i$ is maximal

## Immediate closed form

Tests need only be checked at the two endpoints:

### Strong-keep test

$i \in \mathcal{K}^{++} \iff \Delta_i(\emptyset) > 0$

i.e.

$$\boxed{v_i \;>\; \alpha + \beta \sqrt{q_i}}$$

### Strong-drop test

$i \in \mathcal{D}^{++} \iff \Delta_i(\text{rest}) < 0$, where rest = $\{1..N\} \setminus \{i\}$.

Let $Q_{\text{tot}} = \sum_j q_j$. Then:

$$\boxed{v_i \;<\; \alpha(\sqrt{N} - \sqrt{N-1}) + \beta(\sqrt{Q_{\text{tot}}} - \sqrt{Q_{\text{tot}} - q_i})}$$

Both are $O(N)$ to compute — **milliseconds**.

## Actual numbers on Olist

With $\alpha = 3157.27, \beta = 978.23, N = 2967$:

### Strong-keep threshold

| Seller's $q_i$ | Threshold = $\alpha + \beta\sqrt{q_i}$ | Meaning |
|---|---|---|
| 1 | 3157 + 978 = **4135** BRL | Selling 1 item: pre-IT profit must be > 4135 to be certain-keep |
| 10 | 3157 + 3094 = **6251** BRL | Selling 10 items: must be > 6251 |
| 100 | 3157 + 9782 = **12939** BRL | Selling 100 items: must be > 12939 |
| 1000 | 3157 + 30933 = **34090** BRL | Selling 1000 items: must be > 34090 |

🔍 How many sellers in your table satisfy this? Look at the tail of `pre_it_profits` — **probably very few**. Most sellers' pre-IT profit is far below 4000+ BRL.

### Strong-drop threshold

Assume $Q_{\text{tot}} \approx 100{,}000$ (check via `sellers.quantity.sum()`):

- $\alpha(\sqrt{N} - \sqrt{N-1}) \approx 3157 \times 0.0092 \approx 29$ BRL
- For small $q_i$: $\beta \cdot q_i / (2\sqrt{Q_{\text{tot}}}) \approx 978 \cdot q_i / 632$
  - $q_i = 1 \Rightarrow$ $\beta$-term $\approx 1.5$ → total threshold $\approx 31$ BRL
  - $q_i = 10 \Rightarrow \approx 15$ → total threshold $\approx 44$ BRL
  - $q_i = 100 \Rightarrow \approx 155$ → total threshold $\approx 184$ BRL

So any seller with pre-IT profit **below a few dozen BRL** (or negative) is forcibly removed. This set should be sizeable — every clearly-unprofitable seller lands here.

### Expected outcome

- $\mathcal{K}^{++}$: probably just a few dozen mega-sellers
- $\mathcal{D}^{++}$: probably hundreds to thousands of small loss-making sellers
- $\mathcal{W}^{++}$ = middle ground: possibly thousands of sellers, **much larger than the true $\mathcal{W}$**

The price of the weakening is that the swing set grows and becomes less informative.

## Implementation

```python
import numpy as np

def strong_keep_drop(sellers, alpha=ALPHA, beta=BETA,
                     profit_col='pre_it_profits', qty_col='quantity'):
    v = sellers[profit_col].to_numpy()
    q = sellers[qty_col].to_numpy()
    N = len(sellers)
    Q_tot = q.sum()

    # Strong-keep: v_i > alpha + beta * sqrt(q_i)
    K_plus = v > alpha + beta * np.sqrt(q)

    # Strong-drop: v_i < alpha*(sqrt(N) - sqrt(N-1))
    #              + beta*(sqrt(Q_tot) - sqrt(Q_tot - q_i))
    drop_thresh = alpha * (np.sqrt(N) - np.sqrt(N - 1)) \
                + beta * (np.sqrt(Q_tot) - np.sqrt(Q_tot - q))
    D_plus = v < drop_thresh

    return K_plus, D_plus
```

Quick check:

```python
K_plus, D_plus = strong_keep_drop(sellers)
print(f"Strong must-keep: {K_plus.sum():,} / {len(sellers):,}")
print(f"Strong must-drop: {D_plus.sum():,} / {len(sellers):,}")
print(f"Remaining swing : {(~K_plus & ~D_plus).sum():,}")
```

## Upgrade: iterative tightening (constraint propagation)

The closed-form weakening is too conservative because it considers "any subset" — including impossible extremes (e.g., $S = \emptyset$ cannot occur in an optimum).

We can apply **monotonic tightening** via fixed-point iteration:

```
Let K_lo = sellers confirmed ⊂ every optimum, init = K_plus
Let D_lo = sellers confirmed ⊂ every optimum's complement, init = D_plus

repeat:
    n_lo = |K_lo|         # any optimum's |S| ≥ n_lo
    n_hi = N - |D_lo|     # any optimum's |S| ≤ n_hi
    Q_lo = sum(q[K_lo])
    Q_hi = sum(q[~D_lo])

    for each i ∉ K_lo ∪ D_lo:
        # min Δ_i (worst case)
        # i's environment is: |S| ∈ [n_lo, n_hi-1], Q_S ∈ [Q_lo, Q_hi-q_i]
        worst = min over (|S|, Q_S) in feasible box of:
            v_i - alpha*(sqrt(|S|+1) - sqrt(|S|))
                - beta*(sqrt(Q_S+q_i) - sqrt(Q_S))

        # max Δ_i (best case)
        best = max over the same box of the same expression

        if worst > 0:  add i to K_lo
        if best  < 0:  add i to D_lo

until no new i is added
```

Each iteration uses the previous round's $\mathcal{K}^{++}, \mathcal{D}^{++}$ to shrink the feasible region, making the "worst case" less extreme, so more sellers can be classified.

Upon convergence, $\mathcal{K}_{\text{prop}}, \mathcal{D}_{\text{prop}}$ are still subsets of $\mathcal{K}, \mathcal{D}$ (sound), but **much tighter than the closed-form** version.

### About the min/max within the box

Because the IT marginals are decreasing in $|S|$ and $Q_S$:

- $\Delta_i$ is increasing in $|S|$ → minimum uses $|S| = n_{\text{lo}}$ (or $n_{\text{lo}} - 1$ if $i \in K_{\text{lo}}$)
- $\Delta_i$ is increasing in $Q_S$ → minimum uses $Q_S = Q_{\text{lo}}$ (similar)
- Maximum uses $n_{\text{hi}}, Q_{\text{hi}}$

So the extrema occur at corners of the box, are closed-form-computable, and **each iteration remains $O(N)$**.

The whole propagation typically converges in 5-20 iterations — **total time is seconds**.

## When to use which method

| Method | Soundness | Time | Output |
|---|---|---|---|
| Closed-form weakening | $\mathcal{K}^{++} \subseteq \mathcal{K}$ (conservative) | $O(N)$ ms | Strong must-keep / must-drop, possibly small |
| Iterative tightening | $\mathcal{K}_{\text{prop}} \subseteq \mathcal{K}$ (still conservative, but tight) | $O(NK)$ seconds | Significantly larger than closed-form |
| KKT + sensitivity (previous md) | $\mathcal{K}$ (exact) | $O(K \cdot \text{MISOCP})$ hours | Exact intersection |

**Recommended composition**:

1. Closed-form first to establish a baseline $\mathcal{K}^{++}, \mathcal{D}^{++}$
2. Run iterative propagation to tighten into $\mathcal{K}_{\text{prop}}, \mathcal{D}_{\text{prop}}$
3. Only the remaining candidate swing goes through MISOCP sensitivity (Method 3 of the previous md)

This shrinks step 3's candidate count from hundreds to dozens or fewer — **total time drops from hours to tens of minutes**.

## Relation to ML training

If your end goal is labelling sellers with `y` for supervised learning:

- Sellers in $\mathcal{K}^{++}$: $y = 1$, **100% certain** (not heuristic)
- Sellers in $\mathcal{D}^{++}$: $y = 0$, **100% certain**
- Sellers in $\mathcal{W}^{++}$: label undetermined (discard, or heuristically label with $S^*$)

This gives you a principled **high-quality sample** — training only on certain-label sellers avoids contaminating the model with swing noise.

## Open research questions

1. **Upper bound on propagation convergence rate**: is $O(\log N)$ iterations enough? Verify empirically.
2. **Are box extrema always at corners?** Proven for our objective, but if new constraints are added (e.g., category quotas) it needs re-analysis.
3. **Can propagation alone recover the full $\mathcal{K}, \mathcal{D}$?** In theory the post-propagation swing may not be the true swing — we need to characterise when propagation's output strictly equals the true intersection.
