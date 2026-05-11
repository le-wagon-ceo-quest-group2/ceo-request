"""Page 3: Research Findings — IT cost structure + critique of pre-IT-sorted drops."""

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import numpy as np
import plotly.graph_objects as go

from ._data import load_period_log

dash.register_page(__name__, path="/research-findings", name="Research Findings", order=2)

ALPHA = 3157.27
BETA = 978.23
N_MAX = 3094
I_MAX = 112101

# ----- 3D surface of IT(n, I) -----
n_grid = np.linspace(1, N_MAX, 60)
i_grid = np.linspace(1, I_MAX, 60)
N_mesh, I_mesh = np.meshgrid(n_grid, i_grid)
IT_mesh = ALPHA * np.sqrt(N_mesh) + BETA * np.sqrt(I_mesh)

surface_fig = go.Figure(
    data=[
        go.Surface(
            z=IT_mesh,
            x=N_mesh,
            y=I_mesh,
            colorscale="Viridis",
            colorbar=dict(title="IT cost (BRL)"),
            hovertemplate=(
                "n = %{x:.0f}<br>I = %{y:.0f}<br>IT = %{z:,.0f} BRL<extra></extra>"
            ),
        )
    ]
)
surface_fig.update_layout(
    title="IT(n, I) = α√n + β√I",
    template="plotly_dark",
    height=500,
    margin=dict(t=50, l=10, r=10, b=10),
    scene=dict(
        xaxis_title="n (sellers)",
        yaxis_title="I (items)",
        zaxis_title="IT cost (BRL)",
        camera=dict(eye=dict(x=1.6, y=-1.6, z=0.9)),
    ),
)

# ----- Partial derivative w.r.t. n -----
n_curve = np.linspace(1, N_MAX, 400)
dIT_dn = ALPHA / (2 * np.sqrt(n_curve))
dn_fig = go.Figure()
dn_fig.add_trace(
    go.Scatter(
        x=n_curve, y=dIT_dn,
        mode="lines", line=dict(color="#5DADE2", width=3),
        name="∂IT/∂n",
        hovertemplate="n = %{x:.0f}<br>∂IT/∂n = %{y:.1f} BRL<extra></extra>",
    )
)
dn_fig.update_layout(
    title="∂IT/∂n = α / (2√n)  — marginal cost of one more seller",
    xaxis_title="n (sellers on platform)",
    yaxis_title="BRL per additional seller",
    template="plotly_dark",
    height=350,
    margin=dict(t=50, l=40, r=20, b=40),
    yaxis=dict(type="log"),
)

# ----- Partial derivative w.r.t. I -----
i_curve = np.linspace(1, I_MAX, 400)
dIT_dI = BETA / (2 * np.sqrt(i_curve))
di_fig = go.Figure()
di_fig.add_trace(
    go.Scatter(
        x=i_curve, y=dIT_dI,
        mode="lines", line=dict(color="#F4D03F", width=3),
        name="∂IT/∂I",
        hovertemplate="I = %{x:.0f}<br>∂IT/∂I = %{y:.2f} BRL<extra></extra>",
    )
)
di_fig.update_layout(
    title="∂IT/∂I = β / (2√I)  — marginal cost of one more item",
    xaxis_title="I (cumulative items)",
    yaxis_title="BRL per additional item",
    template="plotly_dark",
    height=350,
    margin=dict(t=50, l=40, r=20, b=40),
    yaxis=dict(type="log"),
)

keep_all = load_period_log("keep_all").copy()
keep_all["cum_post_it"] = keep_all["cum_post_it"].astype(float)

# Find break-even
neg_mask = keep_all["cum_post_it"] < 0
breakeven_idx = neg_mask.idxmin() if neg_mask.any() else 0
breakeven_period = keep_all.loc[breakeven_idx, "period"] if breakeven_idx > 0 else None

# Build cum_post_it chart with shaded cold-start region
cum_fig = go.Figure()

# Negative region as filled area
neg_df = keep_all[keep_all["cum_post_it"] < 0]
if len(neg_df) > 0:
    cum_fig.add_trace(
        go.Scatter(
            x=neg_df["period"],
            y=neg_df["cum_post_it"],
            mode="lines",
            line=dict(color="rgba(231,76,60,0)"),
            fill="tozeroy",
            fillcolor="rgba(231, 76, 60, 0.35)",
            name="Cold-start (cum profit < 0)",
            hoverinfo="skip",
        )
    )

cum_fig.add_trace(
    go.Scatter(
        x=keep_all["period"],
        y=keep_all["cum_post_it"],
        mode="lines+markers",
        line=dict(color="#27AE60", width=3),
        marker=dict(size=7),
        name="Cumulative post-IT profit (no drops)",
    )
)

# Break-even vertical line (manual shape + annotation since x-axis is categorical)
if breakeven_period is not None:
    cum_fig.add_shape(
        type="line",
        x0=breakeven_period, x1=breakeven_period,
        y0=0, y1=1, yref="paper",
        line=dict(color="#F4D03F", width=2, dash="dash"),
    )
    cum_fig.add_annotation(
        x=breakeven_period, y=1, yref="paper",
        text=f"Break-even: {breakeven_period}",
        showarrow=False,
        yanchor="bottom",
        font=dict(color="#F4D03F"),
    )

cum_fig.add_shape(
    type="line",
    x0=0, x1=1, xref="paper",
    y0=0, y1=0,
    line=dict(color="white", width=1),
)
cum_fig.update_layout(
    title="No-drop cumulative post-IT profit over time",
    yaxis_title="cumulative post-IT profit (BRL)",
    template="plotly_dark",
    height=450,
    margin=dict(t=60, l=40, r=40, b=40),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode="x unified",
)

# Where exactly did it cross zero
first_positive_period = keep_all.loc[keep_all["cum_post_it"] > 0, "period"].iloc[0] if (keep_all["cum_post_it"] > 0).any() else "—"
months_underwater = int(neg_mask.sum())

layout = html.Div([
    html.H2("Research Findings"),
    html.P("Observations about the cost structure that shaped strategy design.", className="lead"),

    # ----- Section 1: IT cost properties -----
    html.H3("1. IT cost has monotonically decreasing marginals"),

    dbc.Card(
        dbc.CardBody(
            dcc.Markdown(
                r"""
The platform's IT cost is

$$\mathrm{IT}(n, I) \;=\; \alpha \sqrt{n} \;+\; \beta \sqrt{I}$$

where $n$ = number of sellers on the platform and $I$ = cumulative items sold.
Partial derivatives:

$$\frac{\partial \mathrm{IT}}{\partial n} \;=\; \frac{\alpha}{2\sqrt{n}} \qquad\qquad \frac{\partial \mathrm{IT}}{\partial I} \;=\; \frac{\beta}{2\sqrt{I}}$$

Both are **strictly decreasing** in their arguments (sqrt is concave). The discrete
marginal of admitting a new seller $i$ with $q_i$ items into a platform of size
$(n, I)$ is approximately

$$\Delta\mathrm{IT}_i \;\approx\; \frac{\alpha}{2\sqrt{n}} \;+\; \frac{\beta\, q_i}{2\sqrt{I}}$$

so the bar that seller $i$ must clear to be net-profitable shrinks as either
$n$ or $I$ grows. **Mature, large platforms welcome marginal sellers; tiny
platforms reject them.**
                """,
                mathjax=True,
            )
        ),
        className="mb-4",
    ),

    dbc.Row(
        [
            dbc.Col(dcc.Graph(figure=surface_fig), lg=6),
            dbc.Col(
                [
                    dcc.Graph(figure=dn_fig),
                    dcc.Graph(figure=di_fig),
                ],
                lg=6,
            ),
        ],
        className="mb-4",
    ),

    dbc.Alert(
        [
            html.Strong("Reading the curves: "),
            "both partial derivatives are plotted on a log scale. ",
            "∂IT/∂n drops from ~1,580 BRL/seller at n=1 to ~28 BRL/seller at n=2967 — a 50× decrease. ",
            "∂IT/∂I drops from ~489 BRL/item at I=1 to ~1.5 BRL/item at I=112k — a 300× decrease. ",
            "Both shrink rapidly in the first few hundred entries and flatten thereafter.",
        ],
        color="dark",
        className="mb-4",
    ),

    html.P(
        "Plotting cumulative post-IT profit with no drops applied (the keep_all baseline) "
        "makes the consequence visible:",
        className="text-muted",
    ),

    dcc.Graph(figure=cum_fig),

    dbc.Row(
        [
            dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        html.H4(f"{months_underwater}", className="text-danger"),
                        html.P("months of cold-start before break-even", className="text-muted mb-0"),
                    ])
                ),
                md=4,
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        html.H4(first_positive_period, className="text-warning"),
                        html.P("first month with positive cumulative post-IT", className="text-muted mb-0"),
                    ])
                ),
                md=4,
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        html.H4(f"{keep_all['cum_post_it'].min():,.0f}", className="text-danger"),
                        html.P("deepest cumulative drawdown (BRL)", className="text-muted mb-0"),
                    ])
                ),
                md=4,
            ),
        ],
        className="mb-3 mt-3",
    ),

    dbc.Alert(
        [
            html.H5("Conjecture", className="alert-heading"),
            html.P(
                "Before the platform reaches break-even, no seller should be dropped. "
                "At that point the marginal IT bar is so high that almost every seller "
                "looks individually unprofitable; a naive drop policy would empty the "
                "platform and trap it permanently below break-even. Only after the "
                "marginals amortise (n, I grow) does selective culling make sense.",
                className="mb-0",
            ),
        ],
        color="warning",
        className="mb-4",
    ),

    html.Hr(),

    # ----- Section 2: Critique of pre-IT-sort drops -----
    html.H3("2. Pre-IT-sorted drop list is pure hindsight — and not provably optimal"),

    dbc.Card(
        dbc.CardBody(
            dcc.Markdown(
                r"""
Earlier explorations took the form

```
sort sellers by individual pre-IT profit (ascending)
drop sellers whose pre-IT profit is below some threshold
compute post-IT profit
```

Two problems with this:

1. **It uses future information.** Each seller's "pre-IT profit" is computed
   from their *entire* observed history, including the last month of data.
   Olist's CEO doesn't have this when making real decisions.
2. **It's not provably optimal.** Sorting by individual pre-IT profit ignores
   the non-linear IT cost interactions between sellers. Dropping the marginal
   seller may save less than $\alpha/(2\sqrt{n}) + \beta q_i/(2\sqrt{I})$ — or
   more, depending on the resulting $(n, I)$. There is no theorem saying this
   greedy procedure maximises post-IT profit.
                """,
                mathjax=True,
            )
        ),
        className="mb-3",
    ),

    dbc.Row(
        [
            dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        html.H5("Idea 1 — turn the data into a time series", className="card-title"),
                        html.P([
                            "Rebuild the dataset as a (seller, month) panel. Apply drop strategies ",
                            html.Em("periodically"),
                            ", using only information available up to each decision point. This makes the evaluation honest and lets us simulate any online policy.",
                        ], className="mb-0"),
                    ]),
                    color="info",
                    inverse=True,
                    className="h-100",
                ),
                lg=6,
                className="mb-3",
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        html.H5("Idea 2 — solve for the post-hoc optimum as a yardstick", className="card-title"),
                        html.P([
                            "Find the true optimal subset (allowing full hindsight) and use it as a benchmark. ",
                            html.Strong("If any online strategy reports a post-IT profit above the post-hoc optimum, the implementation must have a bug."),
                            " Cheap and powerful sanity check.",
                        ], className="mb-0"),
                    ]),
                    color="success",
                    inverse=True,
                    className="h-100",
                ),
                lg=6,
                className="mb-3",
            ),
        ]
    ),
])
