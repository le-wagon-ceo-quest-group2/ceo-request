"""Page 2: problem formulation + data."""

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from ._data import load_period_log

dash.register_page(__name__, path="/setup", name="Problem & Data", order=1)

keep_all = load_period_log("keep_all")

active_fig = go.Figure()
active_fig.add_trace(
    go.Bar(
        x=keep_all["period"],
        y=keep_all["n_active"],
        marker_color="#5DADE2",
        name="active sellers",
    )
)
active_fig.update_layout(
    title="Monthly active sellers (keep_all view)",
    template="plotly_dark",
    height=300,
    margin=dict(t=50, l=40, r=40, b=40),
)

it_fig = go.Figure()
it_fig.add_trace(
    go.Scatter(
        x=keep_all["period"],
        y=keep_all["it_cost"],
        mode="lines+markers",
        name="cumulative IT cost",
        line=dict(color="#F4D03F"),
    )
)
it_fig.add_trace(
    go.Scatter(
        x=keep_all["period"],
        y=keep_all["cum_pre_it"],
        mode="lines+markers",
        name="cumulative pre-IT profit",
        line=dict(color="#27AE60"),
    )
)
it_fig.update_layout(
    title="Cumulative pre-IT profit vs IT cost over time",
    template="plotly_dark",
    height=350,
    margin=dict(t=50, l=40, r=40, b=40),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)

layout = html.Div([
    html.H2("The problem"),
    html.P(
        "Olist wants to know: if we had never accepted certain sellers, how much "
        "more would we have earned?",
        className="lead",
    ),

    dbc.Card(
        dbc.CardBody(
            dcc.Markdown(
                r"""
**Subset-optimisation form:**

$$\max_{S \subseteq \text{sellers}} \sum_{i \in S} v_i \;-\; \alpha \sqrt{|S|} \;-\; \beta \sqrt{\textstyle\sum_{i \in S} q_i}$$

- $v_i$: seller $i$'s pre-IT profit (sales commission + subscription − review cost)
- $q_i$: seller $i$'s total item count
- $\alpha = 3157.27$, $\beta = 978.23$ — IT cost coefficients (sqrt amortisation)

**Difficulties:**
- $N = 2967$; brute force $2^N$ infeasible
- Non-convex objective, but the sqrt structure admits an SOCP formulation
- Olist cannot know a seller's full performance up-front — needs an **online strategy**
                """,
                mathjax=True,
            )
        ),
        className="mb-4",
    ),

    html.H2("The dataset"),
    dbc.Row(
        [
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H3("3,094", className="card-title text-info"),
                            html.P("unique sellers", className="card-text"),
                        ]
                    )
                ),
                md=3,
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H3("99,441", className="card-title text-info"),
                            html.P("orders", className="card-text"),
                        ]
                    )
                ),
                md=3,
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H3("112,101", className="card-title text-info"),
                            html.P("items sold", className="card-text"),
                        ]
                    )
                ),
                md=3,
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H3("25 mo", className="card-title text-info"),
                            html.P("2016-09 to 2018-09", className="card-text"),
                        ]
                    )
                ),
                md=3,
            ),
        ],
        className="mb-4",
    ),

    dbc.Row(
        [
            dbc.Col(dcc.Graph(figure=active_fig), md=6),
            dbc.Col(dcc.Graph(figure=it_fig), md=6),
        ]
    ),

    dbc.Alert(
        [
            html.Strong("Cold-start observation: "),
            "cumulative post-IT profit doesn't turn positive until 2017-05 — the first 9 months are net negative due to high IT marginal cost. Any naive 'drop unprofitable sellers' heuristic must therefore include a warmup phase.",
        ],
        color="warning",
        className="mt-3",
    ),
])