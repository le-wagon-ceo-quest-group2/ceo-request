# Olist CEO Request — Should we remove under-performing sellers?

## TL;DR

| Method | post-IT (BRL) | Drops | vs keep_all | Upper-bound capture | Uses future info |
|---|---:|---:|---:|---:|:---:|
| `keep_all` (baseline) | **657,325** | 0 | – | 60% | – |
| Strategy A: warmup + each-3rd-month | **734,798** | 228 | +77K (+12%) | 67% | ❌ |
| Strategy B: warmup + one-shot drop | **774,935** | 281 | +118K (+18%) | 71% | ❌ |
| Strategy A': **no-warmup** + each-3rd-month | **793,588** | 445 | +136K (+21%) | 73% | ❌ |
| **Strategy C: hybrid (first-batch + each-3rd-month)** | **849,861** | **407** | **+193K (+29%)** | **78%** | ❌ |
| Lagrangian / ECOS_BB post-hoc optimum (upper bound) | 1,089,860 | ~850 | +432K | 100% | ✅ |

> All four online strategies — **using historical data only** — outperform the baseline by 12–29%. **Strategy C (hybrid) wins**, stacking A's "continuous monitoring of new cohorts" with B's "catch the grandfathered old sellers". There's still a ~240K BRL gap (22%) to the post-hoc optimum.
>
> 🤯 Counter-intuitive finding (A'): removing the warmup protection actually beats A by +58K BRL. The 3rd-month rule is **itself an implicit warmup** (no seller can be evaluated in their first 2 months), and the platform's new-onboard rate offsets the cold-start damage.
>
> ✅ Sanity check: when `keep_all` the IT cost = 503,145 BRL — matches the problem statement's "cumulative platform IT cost ≈ 500K BRL" exactly.
>
> 📐 All numbers use the **forward-only realised P&L convention**: a dropped seller's cost/profit accrued before the drop stays on the books; only post-drop cost/profit is excluded.

---

## 1. The problem

Olist wants to know: "if we had never accepted certain sellers, how much more would we have earned?" Formalised as a subset optimisation:

$$\max_{S \subseteq \text{sellers}} \sum_{i \in S} v_i - \alpha \sqrt{|S|} - \beta \sqrt{\sum_{i \in S} q_i}$$

- $v_i$: seller $i$'s pre-IT profit (sales commission + subscription − review cost)
- $q_i$: seller $i$'s total item count
- $\alpha = 3157.27, \beta = 978.23$ (IT cost coefficients, sqrt amortisation)

Difficulties:

- N = 2967, brute-force $2^N$ infeasible
- Objective is non-convex, but sqrt is concave → can be written as SOCP
- Olist could not actually know each seller's performance up-front → an **online strategy** is needed

## 2. Post-hoc optimum (theoretical upper bound)

### Solving

Cast as a Mixed-Integer SOCP:

```
max   v · x - α s_n - β s_I
s.t.  s_n ≥ ‖x‖₂                              (boolean trick: ‖x‖² = ‖x‖ since x ∈ {0,1})
      s_I ≥ ‖√q ⊙ x‖₂
      x ∈ {0, 1}^N
```

Solved with cvxpy + ECOS_BB (default free solver). **10 min runtime, 70 MB memory.**

⚠️ Counter-intuitive finding: we initially worried ECOS_BB would not scale, but it actually **outperformed SCIP** — this problem's LP relaxation is very tight (clean KKT-threshold structure), so simple B&B avoids SCIP's cutting-plane / presolving overhead.

### Result

```
Optimal kept:     ~2117 sellers
Optimal dropped:  ~850 sellers
post-IT:          1,089,860 BRL
```

## 3. The online-strategy framework

### Cold-start issue

Early on there are few sellers, so the IT marginal cost ($\alpha/2\sqrt{n} + \beta q/2\sqrt{Q}$) is far higher than any individual seller's profitability. Any naive heuristic would drop everyone, and the platform never gets off the ground. Therefore a strategy needs a **warmup phase**: no evaluations until `cum_post_it_profit > 0`.

### Forward-only realised P&L convention

During simulation, a dropped seller's **realised P&L stays**, **unrealised P&L is excluded**:

- Pre-drop sales commission / subscription / review cost: **all counted** (these were real cash flows)
- Post-drop P&L: **excluded** (the counterfactual never happens)
- IT cost: $\alpha\sqrt{N} + \beta\sqrt{Q}$ where N = all sellers who were ever onboarded, Q = items actually realised (including dropped sellers' pre-drop contributions)

This is the closest convention to real online operations. An earlier version mistakenly used retroactive accounting (wiping all dropped P&L), which distorted the numbers.

### Strategy A: warmup + each-3rd-month

```
Phase 1 (warmup):  no drops while cum_post_it_profit ≤ 0
Phase 2 (active):  each seller's first 2 active months are a grace period;
                   on the 3rd active month, run the closed-form strong-drop
                   test on their first-2-months data:
                       v_obs < α(√n − √(n-1)) + β(√Q − √(Q − q_obs))
                   drop on trigger, never re-evaluate
```

**Result**:

| Metric | Value |
|---|---:|
| Warmup completed | 2017-05 |
| Drops | 228 |
| Pre-IT profit | 1,221,565 BRL |
| IT cost | 486,767 BRL |
| **Post-IT profit** | **734,798 BRL** |

### Strategy B: warmup + one-shot drop

```
Phase 1 (warmup):    no drops while cum_post_it_profit ≤ 0
Phase 2 (one shot):  at the moment warmup completes, evaluate ALL currently
                     active sellers in a single batch using their ENTIRE
                     observed history under the strong-drop test
Phase 3 (passive):   never re-evaluate
```

Compared with A, the difference is only "when, and who, gets evaluated": A evaluates each seller once at their 3rd month; B evaluates every active seller at warmup completion in a single batch (each seller's history = all of their onboard-to-warmup months, up to 9 months).

**Result**:

| Metric | Value |
|---|---:|
| Warmup completed | 2017-05 |
| Drops | 281 |
| Pre-IT profit | 1,249,291 BRL |
| IT cost | 474,356 BRL |
| **Post-IT profit** | **774,935 BRL** |

### Strategy A': A with the warmup protection removed

```
No warmup gate: starting from t = 0,
evaluate any seller whose 3rd active month is exactly t (same ongoing rule as A).
```

Motivation: probe whether "3rd-month rule + current platform marginal cost" really destroys the platform under cold start.

**Result**:

| Metric | Value |
|---|---:|
| Total drops | 445 |
| First drop period | 2016-11 (2 sellers, 2016-09 cohort) |
| Largest single-period drop | 2016-12 (83 sellers, 2016-10 cohort) |
| Pre-IT profit | 1,236,838 BRL |
| IT cost | 443,250 BRL |
| **Post-IT profit** | **793,588 BRL** |

#### Why A' did not destroy the platform

Cold start was expected to make the strategy drop everyone. **It didn't.** Three reasons:

1. **The 3rd-month rule is itself an implicit warmup**: the strategy only evaluates sellers whose 3rd month equals t, so the first two months (2016-09 / 10) see no evaluations at all. By the time of the first evaluation (2016-11), the platform has grown from 2 to 134 sellers.
2. **Threshold scales with q_obs**: threshold = α(√n − √(n-1)) + β·q_obs/(2√Q). The fixed term shrinks fast in n (≈1300 at n=2, ≈137 at n=134), and the variable term scales with the seller's own size, so a medium-sized seller's bar to clear roughly matches their sales income.
3. **New onboard rate > drop rate**: 2016-12 saw 83 drops (out of 41 active that month), but 2017-01 brought in 150 new sellers and the platform bounced back. cum_post_it turns positive at 2017-05 — **the same period as A**, with no delay.

#### Why A' beats A

A's warmup means 522 sellers onboarded between 2016-09 and 2017-02 are **never evaluated** (the grandfathered cohort whose 3rd month falls inside warmup). A' evaluates them at their respective 3rd month and cuts the unprofitable ones early. **Benefit of cutting early > cost of cold-start damage.**

Caveat: this finding is **strongly data-dependent**. Olist's early monthly growth of 100%+ saved A'. On a slow-growth platform, no-warmup could absolutely collapse the system.

### Strategy C: hybrid (first-batch one-shot + ongoing 3rd-month)

```
Phase 1 (warmup):       no drops while cum_post_it_profit ≤ 0
Phase 2 (first batch):  in the period right after warmup completes, evaluate
                        all sellers with ≥ 2 months of history, using their
                        full history under the strong-drop test
Phase 3 (ongoing):      every subsequent month, evaluate any seller whose
                        3rd active month is THIS period (same as A)
```

C is a hybrid of A and B: first-batch fixes A's problem of "old grandfathered sellers never get evaluated"; ongoing fixes B's problem of "post-warmup onboards never get evaluated".

**Result**:

| Metric | Value |
|---|---:|
| Warmup completed | 2017-05 |
| First-batch drops (2017-06) | 190 |
| Ongoing drops (2017-07 to 2018-08) | 217 |
| Total drops | 407 |
| Pre-IT profit | 1,309,935 BRL |
| IT cost | 460,074 BRL |
| **Post-IT profit** | **849,861 BRL** |

### Evaluation-pool comparison across the four strategies

|  | Initial batch evaluation | Subsequent monthly evaluations | Total evaluations | Total drops |
|---|---|---|---:|---:|
| A | 2017-06: ~118 (onboarded 2017-04, throttled by warmup) | each cohort at their 3rd month | ~2,225 | 228 |
| B | 2017-06: 933 (all active) | 0 (never re-evaluated) | 933 | 281 |
| A' | starts 2016-11; evaluates each cohort (including early grandfathered) | every month continuously | ~3,000+ | 445 |
| **C** | 2017-06: 933 (≥ 2 months of history) | each new cohort at their 3rd month | ~2,640 | **407** |

### Why C wins

1. **First batch rescues grandfathered sellers**: the 522 early sellers A misses because "their 3rd month fell inside warmup" — C catches all of those who should be cut.
2. **Ongoing rescues the post-warmup cohort**: the ~1,800 sellers B never evaluates because they onboarded after warmup — C still evaluates them at their 3rd month, stopping the ones that go bad later.
3. **First batch benefits from a long observation window**: early sellers have 5–9 months of data in C's first batch — the review-cost lag is fully visible by then, so judgements are more accurate than A's 2-month window.
4. **Ongoing keeps a short window for early intervention**: post-warmup cohorts still use 2 months of observation in C's ongoing — weaker signal, but enables early stop-loss, and the integration is still net positive.

### Bug-fix history

The early simulator had three accounting bugs:

1. **Sub fee used calendar months** rather than Olist's official `(date_last − date_first).days / 30` (each seller over-counted by ~1.27 months on average)
2. **Dense panel included "ghost months" after last_active** (months after natural churn were charging sub fees)
3. **Final accounting used retroactive** rather than forward-only (dropped sellers' pre-drop P&L was wrongly wiped out)

After fixing all three: keep_all IT cost = 503K, matching the problem's "500K cumulative IT cost" ✅. See `diagnose_pre_it.py`.

## 4. Comparison and interpretation

```
keep_all              =    657,325 BRL              baseline
Strategy A            =    734,798 BRL  (+12%)      warmup + 3rd-month
Strategy B            =    774,935 BRL  (+18%)      warmup + one-shot
Strategy A'           =    793,588 BRL  (+21%)      no-warmup + 3rd-month
Strategy C (hybrid)   =    849,861 BRL  (+29%) ★    ← recommended
Post-hoc optimum      =  1,089,860 BRL  (gap 22%)   theoretical upper bound
```

**All four online strategies clearly beat the baseline; C is currently the best, but still has a 22% gap to the post-hoc optimum**:

- **Positive**: C cuts 407 sellers and recovers 29% of the value — **per-drop yield ~474 BRL/seller**, higher than A, B, or A' — confirming that the hybrid idea (broad sweep over history + continuous monitoring of new cohorts) works.
- **A' vs A counter-intuitive**: removing warmup actually adds +58K BRL, showing warmup gate is over-protection on Olist's data — the 3rd-month rule alone provides a 2-month buffer.
- **Negative**: still 240K BRL (22%) short of the Lagrangian post-hoc optimum, for three reasons:
    1. **The strong-drop test is inherently conservative**: the weakened form only flags sellers who'd be unprofitable in any environment — it misses those who are "barely profitable but raise IT cost"
    2. **Ongoing's 2-month signal is weak**: C's first batch uses 5–9 months and is accurate, but ongoing falls back to 2 months and loses accuracy
    3. **No observation window equals lifetime**: even with C's 9-month first-batch view, you cannot predict how a seller performs in 2018

## 5. Takeaways

1. **Hybrid clearly beats single-policy strategies**: C (first batch + ongoing) beats A, B, A' by 56–115K BRL. The two policies cover different cohorts (A misses grandfathered, B misses post-warmup); combining them resolves both.
2. **Longer observation is more accurate**: C's first batch uses 5–9 months of history and judges well; ongoing falls back to 2 months and loses accuracy. The next obvious experiment is to extend ongoing's window too.
3. **A and B have complementary blind spots**:
    - A's "3rd-month + warmup" rule: sellers onboarded before warmup_period − 2 have their 3rd month inside warmup → **never evaluated**
    - B's "one-shot at warmup" rule: sellers onboarded after warmup → **never evaluated**
    - C stitches both rules together, leaving no seller permanently exempt
4. **Warmup protection may not be necessary** (counter-intuitive A'): A' without warmup still delivers +21% over baseline, +58K BRL over A. The 3rd-month rule **is** an implicit warmup (no seller is evaluated in the first 2 months). But this conclusion is **strongly data-dependent** — Olist's early monthly growth of 100%+ saved A'; a slow-growth platform could collapse without explicit warmup.
5. **Limits of weakened strong-drop in an online setting**: the weakened form only flags sellers who lose money under any environment. But real data contains many sellers who are "marginally profitable but inflate IT cost" — strong-drop misses these. A tighter criterion (true KKT threshold, or marginal contribution) is needed.
6. **Accounting conventions must be strict**: calendar-months × 80 sounds natural but differs from Olist's days/30 convention by ~17%; combined with dense-panel ghost rows and retroactive-vs-forward-only confusion, three bugs together could make a mediocre strategy report 97% capture (fake). After fixing, the true capture is 78%. **Step one for any backtest is to reconcile keep_all and baseline numbers, and verify IT cost ≈ 500K BRL as stated in the problem**.

## 6. Further research directions

- **Multi-window comparison**: run Strategy A with observation windows = 1, 2, 4, 6, 12 months and study false-drop rate and final profit
- **Two-stage strategy**: phase 1 uses B's one-shot for the baseline; phase 2 re-evaluates post-warmup onboards at month 6
- **Threshold safety factor c < 1**: change the drop condition to `v_obs < c × threshold` and try c ∈ {0.5, 0.7, 0.9, 1.2}
- **Lifetime extrapolation**: linearly extrapolate from N months of observation to a typical lifetime, avoiding the systematic v_obs / q_obs underestimate
- **Probabilistic alternatives to rule-based**: use a Beta-Binomial posterior to estimate a seller's true bad-review rate; only drop when ≥ 95% confident
- **NLP signals**: review_comment_message text likely contains strong "bad seller" features (currently unused in the problem)
- **Causal analysis**: correlational evidence is already strong (wait_time → review), but a **causal conclusion** requires more careful experimental design or IV methods
- **Tighter oracle**: the current Lagrangian assumes full hindsight; an ideal oracle should also choose **when** to drop, giving a tighter upper bound

## File index

| File | Purpose |
|---|---|
| `optimum_solvers.py` | Lagrangian fixed-point + MISOCP post-hoc optimum solver |
| `strong_intersection.py` | Weakened closed-form / propagation must-keep / must-drop sets |
| `build_panel.py` | Raw orders/items/reviews → monthly panel parquet (with sub_fee_t) |
| `strategy_warmup_3rd_month.py` | Strategy A: warmup + each-3rd-month evaluation |
| `strategy_one_shot_drop.py` | Strategy B: warmup + one-shot drop at completion |
| `strategy_no_warmup.py` | Strategy A': no warmup + each-3rd-month evaluation |
| `strategy_hybrid.py` | **Strategy C: first-batch + ongoing 3rd-month (recommended)** |
| `diagnose_pre_it.py` | Diagnose the sub-fee accounting inconsistency |
| `data/panel_monthly.parquet` | 21,856 row (seller, month) long table (with sub_fee_t) |
| `data/sellers_meta.parquet` | 3,094 row seller metadata (with months_on_olist) |