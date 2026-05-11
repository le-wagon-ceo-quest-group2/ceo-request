# CEO Request — Presentation Script

Estimated runtime: **~10 minutes** for a 3-person group (rough split below).

---

## 🎤 Slide 1 — Cover (≈ 30 s)  [speaker: Hang]

> "Hi everyone, we're Group 2 — Hang, Mario, and Soodabeh — and today we're presenting our take on the Olist CEO request: **should we remove under-performing sellers?**"
>
> "Instead of jumping straight into 'yes/no/who', we spent most of our time on a more fundamental question: **what does it even mean to do this well?** That question shaped everything that follows."

→ click navbar **Research Findings**

---

## 🔬 Slide 2 — Research Findings (≈ 2 min)  [speaker: Hang]

> "The first thing we noticed is that the IT cost has a very specific shape."
>
> *(point to the 3D surface)* "It's α√n + β√I — concave in both the number of sellers and the cumulative items. So adding the first seller costs about 1,500 BRL on the margin, but adding the 3,000th seller costs only about 28 BRL. The partial derivatives on the right make this concrete — both drop by 50× to 300× as the platform grows."

> "Now look at the cumulative profit curve at the bottom *(point)*. With no drops at all, the platform spends its first **9 months underwater** — losing up to 65K BRL — before turning positive in May 2017."

> "This led to our first **conjecture**: any strategy that drops sellers during this red zone will likely cannibalise the platform itself, because IT marginal cost is just too high relative to anyone's individual profit. **Don't drop anyone before break-even.**"

> "The second observation was about methodology. Earlier explorations sorted sellers by individual pre-IT profit and cut the bottom — but this approach has two problems. First, it uses **future information**: pre-IT profit needs to know each seller's full lifetime. Olist can't see that at onboarding. Second, **even ignoring that, it's not provably optimal** — the non-linear IT cost interactions mean greedy sorting can leave money on the table."

> "So we needed two new pieces: an **online evaluation framework** that respects causality, and a **post-hoc upper bound** to measure ourselves against."

→ click navbar **Post-hoc Optimum**

---

## 🎯 Slide 3 — Post-hoc Optimum (≈ 2 min)  [speaker: Mario]

> "The clairvoyant question is: with full hindsight, what's the maximum post-IT profit we could have made by choosing the right subset of sellers?"

> "Brute force is hopeless — 2^N subsets means about 10^893 candidates, which is more than the atoms in the universe by a factor of 10^800. So we cast it as a **Mixed-Integer Second-Order Cone Program**."

> "The trick is to introduce auxiliary variables s_n and s_I, write the sqrt terms as SOC constraints, and exploit the **boolean identity** that ||x||² = ||x|| when x is 0/1. This turned out to be solvable with the free `cvxpy` + `ECOS_BB` solver. We initially worried that ECOS_BB wouldn't scale — but actually it outperformed SCIP, because the LP relaxation here is unusually tight."

> "The answer: keeping about **2,117 sellers** out of 2,967 yields **1,089,860 BRL** in post-IT profit. That's our upper bound."

> "But we wanted more than just one optimum — we wanted to characterise **which sellers are must-keep across all optima**. We exploited the IT-cost monotonicity from earlier: a seller's marginal contribution is bounded below by its value at the empty platform, and bounded above by its value at the full platform. So we built a closed-form propagation that iteratively tightens these bounds."

> "Empirically, **must-keep was empty** — no seller is so essential that the optimum can't survive without them. And **must-drop matched the MISOCP's drop list within ±5 sellers** — strong corroboration. The caveat is: matching is suggestive but not a uniqueness proof. We have not certified that this is the unique optimum."

→ click navbar **Strategies**

---

## 📋 Slide 4 — Online Strategies (≈ 2 min)  [speaker: Mario]

> "Armed with the upper bound, we designed four online strategies. All four use **historical data only** — no future leakage — and all four use the same closed-form strong-drop test. They differ only in **when and who** to evaluate."

> *(point to Strategy A card)* "**Strategy A** has a warmup phase: no drops until the platform is profitable. After that, each seller is evaluated once at their 3rd active month. It captures 67% of the upper bound — solid baseline."

> *(Strategy B)* "**Strategy B** also warms up, but at the moment warmup completes, it evaluates *every* active seller in a single one-shot batch — each seller has 5 to 9 months of history at that point. 71% capture. Slightly better, because the long observation window is more accurate, but it misses everyone onboarded after warmup."

> *(Strategy A')* "**Strategy A prime** is a sanity-check variant: drop the warmup entirely. This was supposed to fail catastrophically — and it didn't. 73% capture, +58K BRL over A. The reason is that the 3rd-month rule is **itself an implicit warmup**: nobody can be evaluated in their first two months, and by the time the third month comes the platform has usually grown enough to absorb the drops. **But this finding is data-dependent** — Olist's early growth was 100%+ per month, which saved A'. A slower platform might collapse without explicit warmup."

> *(Strategy C — emphasise)* "**Strategy C is our recommendation.** It's a hybrid: one batch evaluation at warmup completion (long history, very accurate, catches the grandfathered cohort), and from then on each new cohort gets evaluated at their 3rd month (short window, but catches later deterioration). **78% capture, +29% over baseline**, dropping 407 of 2,967 sellers."

→ click navbar **Trajectories**

---

## 📈 Slide 5 — Trajectories (≈ 1.5 min)  [speaker: Soodabeh]

> "This chart shows cumulative post-IT profit over time for all five paths."

> "Notice that *all* strategies are negative for the first 9 months — that's the cold-start zone we identified earlier. Then they all turn positive around May 2017, which corresponds to Olist breaking even."

> "After that, the strategies start to separate. Strategy C — the green line — pulls ahead because it cuts both the old grandfathered sellers and the new cohorts as they emerge. By the end of the horizon, C is roughly 200K above keep_all."

> *(point to the lower-left chart — active sellers)* "You can also see the consequences of each strategy on platform size. A' has that visible **dip in December 2016** when 83 sellers get dropped in one go — but the platform recovers within two months thanks to new onboards."

> *(point to lower-right — cumulative drops)* "And here you can see the drop timing — A and C have continuous drops over time, B has a single spike at warmup, A' starts much earlier."

→ click navbar **Takeaways**

---

## 🏁 Slide 6 — Takeaways & Recommendation (≈ 2 min)  [speaker: Soodabeh]

> "Six lessons from this study."

> "**One**, hybrid strategies clearly beat single-policy ones. By combining A's continuous monitoring with B's long-history batch, C captures cohorts that either policy alone would miss."

> "**Two**, longer observation windows are more accurate. C's first batch uses 5–9 months and gets it right; the ongoing 2-month evaluations are weaker. Extending the ongoing window is the obvious next experiment."

> "**Three**, A and B have complementary blind spots — A grandfathers the early cohort, B grandfathers the late cohort. C stitches both holes."

> "**Four**, warmup protection may not be necessary on fast-growing platforms — but this is strongly data-dependent."

> "**Five**, the weakened strong-drop test is inherently conservative. It only catches sellers who lose money in every environment; it misses sellers who are 'barely profitable but inflate IT cost'. A tighter criterion would help."

> "**Six** — and this is the most important methodological lesson — **accounting conventions must be strict**. Our first version had three accounting bugs combined that made a mediocre strategy look like a 97% capture. After fixing all three, the true number was 78%. Always reconcile keep_all against the problem statement first — IT cost should be roughly 500K BRL, otherwise something is wrong."

> *(switch to recommendation alert)* "**Our recommendation to the CEO**: deploy Strategy C. It's operationally simple — one one-shot evaluation of current sellers, then a recurring check on each new seller at their third month. No ML model required, just a closed-form rule. Expected uplift: 29% over the status quo on the historical horizon."

→ pause for questions

---

## 🎤 Q&A talking points

If asked... ↓

**"Why not just use the upper bound — drop those 850 sellers and be done?"**
> Because the upper bound uses every seller's full lifetime data, which Olist cannot have at decision time. The whole point of the online framework is to **simulate what would have been achievable in real-time**. The upper bound is a measuring stick, not a deployable policy.

**"Strategy A' beats A — is warmup pointless?"**
> Not in general. Olist's data has unusually fast early growth (100%+ per month). On a slower platform, A' could deplete the seller pool faster than it replenishes, never reaching break-even. Warmup is cheap insurance; we'd keep it as a safety net.

**"How big is the gap to the upper bound, and can we close it?"**
> 22% — about 240K BRL on this horizon. Closing it would require either tighter judgement criteria (true KKT threshold instead of weakened strong-drop), longer ongoing observation windows, or richer signals like NLP on review text. None of these are out of reach; the framework is in place to test them.

**"Did you account for customer behaviour after a seller is dropped?"**
> No, we assumed customer behaviour is exogenous — dropping a seller removes their orders but doesn't redirect demand to others. It's a simplification. A more sophisticated model would include substitution effects.

---

## 📝 Speaker notes / delivery tips

- Don't read the slides; reference them
- Numbers to know cold: **+29% C vs baseline**, **78% upper-bound capture**, **407 dropped sellers**, **500K IT cost sanity check**
- The Cover slide should take 30 seconds — don't dwell
- Slow down on the partial-derivative section; that's the conceptual centre
- The "ECOS_BB beats SCIP" anecdote is a nice colour story — drop it if short on time
- Save 1 minute buffer for questions; if you're running over, cut the Q&A talking points
