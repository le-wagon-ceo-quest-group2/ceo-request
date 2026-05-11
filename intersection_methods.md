# Computing the must-keep / must-drop sets across all global optima

## Formalisation

Let the global optimum value be $\Pi^* = \max_{x \in \{0,1\}^N} \Pi(x)$, and let the set of all solutions attaining $\Pi^*$ be:

$$\mathcal{S}^* = \{ S \subseteq \{1, \ldots, N\} \;:\; \Pi(\mathbb{1}_S) = \Pi^* \}$$

We want three sets:

| Name | Definition | Meaning |
|---|---|---|
| **Must-keep** $\mathcal{K}$ | $\displaystyle\bigcap_{S \in \mathcal{S}^*} S$ | Sellers kept by every optimum |
| **Must-drop** $\mathcal{D}$ | $\displaystyle\bigcap_{S \in \mathcal{S}^*} S^c \;=\; \left(\bigcup_{S \in \mathcal{S}^*} S\right)^c$ | Sellers dropped by every optimum |
| **Swing** $\mathcal{W}$ | $\{1..N\} \setminus (\mathcal{K} \cup \mathcal{D})$ | In some optima, out of others |

**Key invariant**: $\mathcal{K}, \mathcal{D}, \mathcal{W}$ are deterministic outputs of the problem, independent of which particular optimum a solver returns.

## Three methods

### Method 1 — naive sensitivity test (exact, 2N solves)

For each seller $i$ verify independently:

```
solve_in(i)  = max profit  s.t. x_i = 1
solve_out(i) = max profit  s.t. x_i = 0
```

| Outcome | Classification |
|---|---|
| `solve_in(i) = Π*` and `solve_out(i) < Π*` | $i \in \mathcal{K}$ |
| `solve_out(i) = Π*` and `solve_in(i) < Π*` | $i \in \mathcal{D}$ |
| `solve_in(i) = solve_out(i) = Π*` | $i \in \mathcal{W}$ |

**Correctness**: if `solve_in(i) = Π*` then there exists an optimum containing $i$; if simultaneously `solve_out(i) < Π*` then no optimum excludes $i$ → $i$ must be in. The dual argument applies for must-drop.

**Cost**: 2N MISOCPs. Infeasible directly for N=2967.

### Method 2 — iterative no-good cut (exact, K solves)

Enumerate all optima:

```
S₁ ← solve()
S_list ← [S₁]
while True:
    S_next ← solve_with_constraints([
        cp.sum( S_k ⊙ (1 − x) + (1 − S_k) ⊙ x ) ≥ 1   for each S_k in S_list
    ])
    if profit(S_next) < Π* − ε: break
    S_list.append(S_next)

K = ⋂ S_list
D = complement of ⋃ S_list
```

The cut forces each new solution to differ from every known one by **at least one seller**.

**Cost**: K + 1 solves (K = number of distinct optima). If the swing set is large, K can explode (worst case $2^{|\mathcal{W}|}$).

### Method 3 — KKT pruning + targeted sensitivity (recommended)

Exploit problem structure. At any global optimum $S^*$:

$$i \in S^* \iff v_i \;>\; \tau_i := \frac{\alpha}{2\sqrt{n^*}} + \frac{\beta q_i}{2\sqrt{I^*}}$$

Define the KKT slack:

$$\Delta_i := v_i - \tau_i$$

- $\Delta_i \gg 0$: seller is in every optimum (strong incentive to keep)
- $\Delta_i \ll 0$: seller is in no optimum
- $|\Delta_i|$ small: candidate swing

**Pruning steps**:

1. Run MISOCP once to obtain $S^*$, $\Pi^*$, $(n^*, I^*)$, $\tau$
2. Compute all $\Delta_i$
3. Take the K sellers with smallest $|\Delta_i|$ as swing candidates (K ≈ 100–300)
4. For the remaining N−K sellers, assign by sign of $\Delta_i$ to $\mathcal{K}$ or $\mathcal{D}$ (**heuristic — see verification below**)
5. Run Method 1 on each of the K candidates (warm-started, seconds each)
6. Merge: $\mathcal{K}$ = non-swing with $\Delta > 0$ + candidates verified as must-keep; analogously for $\mathcal{D}$

**Cost**: 1 + 2K solves. For N=2967 and K=200 → 401 solves, manageable.

**Rigour caveat**: step 4 treats "sellers far from the threshold cannot be swing" as a fact. This is actually a **strong assumption** that requires proof:

> Lemma (to prove): if $\Delta_i > \epsilon^*$ (some explicit constant $\epsilon^*$), then $i \notin \mathcal{W}$.

Intuition: removing $i$ from $S^*$ without compensating substitutions would drop profit by at least $\Delta_i$; but other optima might compensate by including different sellers, so a rigorous threshold must account for the maximum possible swap compensation.

**In practice**: take $\epsilon^* = \max_i |q_i| \cdot \beta / \sqrt{I^*}$ as a conservative threshold, and use Method 1 to verify that no "non-swing" seller was wrongly assigned. If a few candidates turn out not to be swing, your pruning was generous; if too many show up as swing, increase K.

### Method 4 — profit-equality dual LP (theoretically elegant)

Add profit-equals-optimum as a constraint, and for each seller solve max/min of $x_i$:

```
For all i:
    x_i_max = max  x_i  s.t. profit(x) ≥ Π* − ε
    x_i_min = min  x_i  s.t. profit(x) ≥ Π* − ε
```

| Outcome | Classification |
|---|---|
| $x_i^{\max} = x_i^{\min} = 1$ | $i \in \mathcal{K}$ |
| $x_i^{\max} = x_i^{\min} = 0$ | $i \in \mathcal{D}$ |
| $x_i^{\max} = 1$ and $x_i^{\min} = 0$ | $i \in \mathcal{W}$ |

Same cost as Method 1 (2N solves), but each subproblem has a minimal objective (linear in one variable), so could be faster. Requires solver support for max/min under equality constraints.

## Recommended pipeline

For Olist's N=2967 reality:

```
1. solve MISOCP once  → S*, Π*, (n*, I*), τ
2. compute Δ_i = v_i − τ_i
3. take K=200 sellers with smallest |Δ_i| as candidate swing
4. heuristic assignment of non-candidates:
       Δ_i > 0 → K_hat
       Δ_i < 0 → D_hat
5. for each candidate i: warm-start solve(x_i=1) and solve(x_i=0)
6. refine candidates → exact K_swing, D_swing, W
7. verification: spot-check several K_hat / D_hat entries with small |Δ_i|
8. output:
       K = K_hat ∪ K_swing
       D = D_hat ∪ D_swing
       W = remaining candidates
```

Pseudocode:

```python
def find_keep_drop_sets(sellers, K_swing=200, alpha=ALPHA, beta=BETA):
    v = sellers['pre_it_profits'].values
    q = sellers['quantity'].values
    N = len(sellers)

    # 1) one master solve
    S_star = solve_misocp(sellers)        # bool mask
    Pi_star = total_profit(S_star, v, q)
    n_star = int(S_star.sum())
    I_star = float(q[S_star].sum())

    # 2) KKT slack
    tau = alpha / (2 * np.sqrt(n_star)) + beta * q / (2 * np.sqrt(I_star))
    delta = v - tau

    # 3) candidate swing
    candidate_idx = np.argsort(np.abs(delta))[:K_swing]
    is_candidate = np.zeros(N, dtype=bool); is_candidate[candidate_idx] = True

    # 4) heuristic assignment for non-candidates
    K_hat = (~is_candidate) & (delta > 0)
    D_hat = (~is_candidate) & (delta < 0)

    # 5) for each candidate: 2 fixed-MISOCP runs (warm-started)
    K_swing_set = np.zeros(N, dtype=bool)
    D_swing_set = np.zeros(N, dtype=bool)
    W_set       = np.zeros(N, dtype=bool)

    for i in candidate_idx:
        p_in  = solve_with_fixed(sellers, i, 1, warm=S_star)
        p_out = solve_with_fixed(sellers, i, 0, warm=S_star)
        in_optimal  = (p_in  >= Pi_star - 1e-6)
        out_optimal = (p_out >= Pi_star - 1e-6)
        if in_optimal and not out_optimal:
            K_swing_set[i] = True
        elif out_optimal and not in_optimal:
            D_swing_set[i] = True
        elif in_optimal and out_optimal:
            W_set[i] = True
        # both infeasible can't happen (S* itself satisfies one)

    return K_hat | K_swing_set, D_hat | D_swing_set, W_set
```

## Complexity estimate

With K=200:

| Stage | Count | Per call | Total |
|---|---|---|---|
| Master solve | 1 | 10 min | 10 min |
| Candidate verification | 400 | 30 s (warm-start) | 200 min ≈ 3.3 h |
| Spot-check | ~20 | 30 s | 10 min |
| **Total** | | | **≈ 3.5–4 hours** |

In practice ECOS_BB may not have native warm-start; cvxpy provides initial-value hints. Without warm-start, every solve still takes ~10 min, total 70 hours — infeasible. We'd need to switch to Gurobi/MOSEK (warm-start support) or shrink K further.

## Verification & debugging

After running, do a few sanity checks:

```python
# 1. K, D, W are disjoint, union = full set
assert (K & D).sum() == 0
assert (K & W).sum() == 0
assert (D & W).sum() == 0
assert (K | D | W).sum() == N

# 2. K should be a subset of S* (must-keep ⊂ any single optimum)
assert K.sum() <= S_star.sum()
assert (K & ~S_star).sum() == 0

# 3. D must not intersect S*
assert (D & S_star).sum() == 0

# 4. upper-bound check: dropping any K seller must lower profit
for i in np.random.choice(np.where(K)[0], 5, replace=False):
    p = solve_with_fixed(sellers, i, 0)
    assert p < Pi_star - 1e-6, f"seller {i} marked K but droppable"
```

If any assertion fails, pruning was too aggressive — increase K.

## Open research questions

1. **Precise characterisation of $\epsilon^*$**: can we derive an **explicit, computable, tight upper bound** that strictly guarantees $\Delta_i > \epsilon^* \Rightarrow i \notin \mathcal{W}$? This is the key to upgrading Method 3 into a rigorous algorithm.

2. **SOC equality modelling for Method 4**: the profit-equality must be written as `profit ≥ Π* − ε` in cvxpy (a convex constraint), but that gives an $\epsilon$-optimal set, not the exact optimum. How do we model "profit = optimum" rigorously? Requires `profit ≥ Π*` (theoretically convex but possibly numerically infeasible).

3. **Multiple KKT equilibria**: if there exist optima $S_1^*, S_2^*$ with $|S_1^*| \neq |S_2^*|$ (different $n^*$), Method 3's pruning threshold must be intersected over all possible $(n, I)$ — significantly harder.

4. **Maximum possible $|\mathcal{W}|$**: can we bound $|\mathcal{W}|$ above? This affects Method 2's worst case. Olist's discretised review_cost values suggest $|\mathcal{W}|$ may be non-trivial.

## Recommended first steps

1. **Run one master solve** and plot a histogram of $\Pi^*$ and $\Delta$ — see how sparse the tails of $|\Delta|$ are; this calibrates K.
2. **Run Method 1 on the 20 smallest-$|\Delta|$ sellers** to see how many actually fall into swing. Zero swings → pruning has lots of headroom, K can be small; half swings → K must grow.
3. **Run 10 iterations of Method 2** to count distinct optima and check whether their $(n, I)$ are the same — answers "is there a unique KKT equilibrium?".

These three together calibrate the true shape of the swing set, after which Method 3 or its variants can be deployed in earnest.
