"""Page 4: post-hoc upper bound — MISOCP + must-keep/must-drop iterative bound."""

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

from ._data import UPPER_BOUND

dash.register_page(__name__, path="/upper-bound", name="Post-hoc Optimum", order=3)

layout = html.Div([
    html.H2("Post-hoc Optimum"),
    html.P(
        "What is the highest post-IT profit attainable with full hindsight? Two angles: a direct MISOCP solver and an iterative closed-form bound.",
        className="lead",
    ),

    # ----- Problem statement -----
    html.H3("Problem statement"),
    dbc.Card(
        dbc.CardBody(
            dcc.Markdown(
                r"""
Choose a subset $S \subseteq \{1, \ldots, N\}$ of sellers to maximise

$$\Pi(S) \;=\; \sum_{i \in S} v_i \;-\; \alpha\sqrt{|S|} \;-\; \beta\sqrt{\textstyle\sum_{i \in S} q_i}$$

where $v_i$ is seller $i$'s pre-IT profit (full lifetime, hindsight) and $q_i$ is their total item count.
                """,
                mathjax=True,
            )
        ),
        className="mb-4",
    ),

    # ----- Difficulty -----
    html.H3("Why brute force fails"),
    dbc.Card(
        dbc.CardBody(
            dcc.Markdown(
                r"""
The number of subsets is

$$\sum_{n=0}^{N} \binom{N}{n} \;=\; 2^N$$

so for $N = 2967$ there are $2^{2967}$ candidates — roughly $10^{893}$, more
than the atoms in the observable universe by ~800 orders of magnitude. No
exhaustive search.
                """,
                mathjax=True,
            )
        ),
        className="mb-4",
    ),

    # ----- SOCP approach -----
    html.H3("Approach 1 — Mixed-Integer SOCP"),
    dbc.Row(
        [
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        dcc.Markdown(
                            r"""
Cast as an MISOCP using the boolean trick ($\|x\|^2 = \|x\|$ for $x \in \{0,1\}^N$):

$$\begin{aligned}
\max_{x, s_n, s_I} \quad & v^T x - \alpha\, s_n - \beta\, s_I \\
\text{s.t.}\quad & s_n \;\geq\; \|x\|_2 \\
& s_I \;\geq\; \|\sqrt{q} \odot x\|_2 \\
& x \;\in\; \{0,1\}^N
\end{aligned}$$

Solved with `cvxpy` + **ECOS_BB** (Branch-and-Bound on top of the open-source
ECOS conic solver). The LP/SOCP relaxation is unusually tight here (clean
KKT-threshold structure), so naive B&B does very few branches.
                            """,
                            mathjax=True,
                        )
                    )
                ),
                lg=7,
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        html.H4("Result", className="card-title"),
                        html.H1(f"{UPPER_BOUND:,.0f}", className="text-success"),
                        html.P("BRL post-IT profit", className="text-muted"),
                        html.Hr(),
                        dbc.Row([
                            dbc.Col([
                                html.H4("~2,117", className="text-info"),
                                html.P("kept", className="small text-muted"),
                            ]),
                            dbc.Col([
                                html.H4("~850", className="text-warning"),
                                html.P("dropped", className="small text-muted"),
                            ]),
                        ]),
                        html.Hr(),
                        html.Small("Runtime: ~10 min, ~70 MB memory (ECOS_BB).", className="text-muted"),
                    ])
                ),
                lg=5,
            ),
        ],
        className="mb-4",
    ),

    # ----- Uniqueness consideration -----
    html.H3("Is the optimum unique?"),
    dbc.Card(
        dbc.CardBody(
            dcc.Markdown(
                r"""
The MISOCP returns *some* optimal subset, not necessarily the only one. There may be
several subsets achieving the same $\Pi^*$. So we look at two derived sets:

- **Strong-must-keep** $\mathcal{K} \;=\; \bigcap_{S^* \in \text{optima}} S^*$ — sellers kept by *every* optimum
- **Strong-must-drop** $\mathcal{D} \;=\; \bigcap_{S^* \in \text{optima}} (S^*)^c$ — sellers dropped by *every* optimum

These are robust facts about the problem, independent of which particular optimum a solver returns.
                """,
                mathjax=True,
            )
        ),
        className="mb-4",
    ),

    # ----- Approach 2: iterative bound -----
    html.H3("Approach 2 — Iterative closed-form bound on \U0001D4A6 and \U0001D49F"),
    dbc.Card(
        dbc.CardBody(
            dcc.Markdown(
                r"""
Use the IT-cost monotonicity we observed earlier. Adding seller $i$ to a set with
$|S| = n$ sellers and total quantity $I$ gives marginal profit

$$\Delta\Pi_i(n, I) \;\approx\; v_i \;-\; \frac{\alpha}{2\sqrt{n}} \;-\; \frac{\beta\, q_i}{2\sqrt{I}}$$

Since the RHS is increasing in $n$ and $I$:

- $\Delta\Pi_i$ is **smallest at $(n, I) = (0, 0)$** (empty platform, worst case)
- $\Delta\Pi_i$ is **largest at $(n, I) = (N{-}1, Q_{\text{tot}}{-}q_i)$** (full platform minus self, best case)

So we can derive **closed-form admissibility tests**:

- If $\Delta\Pi_i(0, 0) > 0$, seller $i$ is profitable even at the empty platform — they must be in every optimum, hence $i \in \mathcal{K}$.
- If $\Delta\Pi_i(N{-}1, Q_{\text{tot}}{-}q_i) < 0$, seller $i$ loses money even with the largest possible platform — they must be in no optimum, hence $i \in \mathcal{D}$.

These conditions establish a first batch of provably-in / provably-out sellers.
They can then be used to **tighten** the bounds on the unknown sellers:

```
1. K_lo = sellers passing the strong-keep test at current (n_lo, I_lo)
2. D_lo = sellers failing the strong-drop test at current (n_hi, I_hi)
3. Update n_lo += |K_lo|, n_hi −= |D_lo|, I_lo += q(K_lo), I_hi −= q(D_lo)
4. Re-test undecided sellers under the tighter (n_lo, I_lo, n_hi, I_hi)
5. Repeat until no new seller is admitted to K or D → fixed point
```

The fixed point gives a **conservative sub-set of the true $\mathcal{K}$ and
$\mathcal{D}$** — we may miss some members, but we never include a wrong one.
                """,
                mathjax=True,
            )
        ),
        className="mb-4",
    ),

    # ----- Result of iteration -----
    html.H3("Empirical result on Olist data"),
    dbc.Row(
        [
            dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        html.H5("Strong-must-keep \U0001D4A6"),
                        html.H2("0 sellers", className="text-secondary"),
                        html.P(
                            "No seller is profitable at the empty platform — the "
                            "fixed IT cost α dominates. We cannot prove anyone is "
                            "absolutely necessary.",
                            className="text-muted small mb-0",
                        ),
                    ])
                ),
                md=6,
                className="mb-3",
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        html.H5("Strong-must-drop \U0001D49F"),
                        html.H2("~845 sellers", className="text-warning"),
                        html.P(
                            "Matches (within ±5) the drop set returned by the "
                            "MISOCP solver — strong corroboration that this is "
                            "the right set to cut.",
                            className="text-muted small mb-0",
                        ),
                    ])
                ),
                md=6,
                className="mb-3",
            ),
        ]
    ),

    dbc.Alert(
        [
            html.H5("Caveat: matching ≠ proof of uniqueness", className="alert-heading"),
            html.P(
                "The fact that the iterative \U0001D49F matches MISOCP's drop list is suggestive "
                "but not a uniqueness proof. There could in principle still be alternative "
                "optima that swap sellers within the un-decided middle. Establishing strict "
                "uniqueness would require a separate certificate (e.g., a Lagrangian dual "
                "argument), which we have not produced.",
                className="mb-0",
            ),
        ],
        color="info",
        className="mb-4",
    ),

    # ----- Next idea -----
    html.H3("Where this points next"),
    dbc.Alert(
        [
            html.P([
                "The iterative \U0001D49F set is a ",
                html.Em("near-optimal drop list with full hindsight"),
                ". Naively applying it as a one-shot drop policy is still hindsight — "
                "we need each seller's full pre-IT profit to evaluate the conditions. But "
                "the structure suggests an online variant:",
            ]),
            html.Ul([
                html.Li("Periodically estimate each active seller's pre-IT profit from data observed so far"),
                html.Li("Re-run the iterative tightening at each decision point using current platform state"),
                html.Li("Apply the resulting \U0001D49F as the drop list for that period"),
            ]),
            html.P([
                "This becomes a candidate online policy, evaluated against the MISOCP upper bound to measure how much of the post-hoc optimum it captures.",
            ], className="mb-0"),
        ],
        color="primary",
    ),
])
