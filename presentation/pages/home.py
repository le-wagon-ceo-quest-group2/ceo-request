"""Page 1: TL;DR."""

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from ._data import load_summary, STRATEGY_COLOUR, UPPER_BOUND

dash.register_page(__name__, path="/tldr", name="TL;DR", order=0)

summary = load_summary()

bar = go.Figure()
bar.add_trace(
    go.Bar(
        x=summary["display"],
        y=summary["final_post_it_profit"],
        text=[f"{v:,.0f}" for v in summary["final_post_it_profit"]],
        textposition="outside",
        marker_color=[STRATEGY_COLOUR[s] for s in summary["strategy"]],
        name="post-IT profit",
    )
)
bar.add_hline(
    y=UPPER_BOUND,
    line_dash="dash",
    line_color="red",
    annotation_text=f"Post-hoc upper bound: {UPPER_BOUND:,.0f}",
    annotation_position="top right",
)
bar.update_layout(
    title="Final post-IT profit by strategy",
    yaxis_title="post-IT profit (BRL)",
    template="plotly_dark",
    height=500,
    yaxis=dict(range=[0, UPPER_BOUND * 1.1]),
    margin=dict(t=60, l=40, r=40, b=40),
)


def _fmt_money(v):
    return f"{v:,.0f}"


def _fmt_delta(v):
    if v == 0:
        return "—"
    sign = "+" if v > 0 else "−"
    return f"{sign}{abs(v):,.0f}"


table_rows = []
for _, r in summary.iterrows():
    table_rows.append(
        html.Tr(
            [
                html.Td(r["display"]),
                html.Td(f"{int(r['total_dropped']):,}", style={"textAlign": "right"}),
                html.Td(_fmt_money(r["final_post_it_profit"]), style={"textAlign": "right"}),
                html.Td(_fmt_delta(r["vs_baseline"]), style={"textAlign": "right"}),
                html.Td(f"{r['upper_capture_pct']:.1f}%", style={"textAlign": "right"}),
            ]
        )
    )

table = dbc.Table(
    [
        html.Thead(
            html.Tr(
                [
                    html.Th("Strategy"),
                    html.Th("Drops", style={"textAlign": "right"}),
                    html.Th("post-IT (BRL)", style={"textAlign": "right"}),
                    html.Th("vs baseline", style={"textAlign": "right"}),
                    html.Th("Upper-bound capture", style={"textAlign": "right"}),
                ]
            )
        ),
        html.Tbody(table_rows),
    ],
    striped=True,
    bordered=True,
    hover=True,
    color="dark",
    responsive=True,
)


def _info_card(title, body, colour):
    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.H5(title, className="card-title"),
                    html.P(body, className="card-text mb-0"),
                ]
            )
        ],
        color=colour,
        inverse=True,
        className="mb-3 h-100",
    )


layout = html.Div([
    html.H1("Olist CEO Request", className="display-3"),
    html.P(
        "Should we remove under-performing sellers? — and if so, can we decide it online?",
        className="lead",
    ),
    html.Hr(),

    dbc.Row(
        [
            dbc.Col(table, lg=6),
            dbc.Col(dcc.Graph(figure=bar), lg=6),
        ],
        className="mb-4",
    ),

    dbc.Row(
        [
            dbc.Col(
                _info_card(
                    "Best online strategy: C (hybrid)",
                    "+29% vs keep_all baseline, captures 78% of the post-hoc optimum using historical data only.",
                    "success",
                ),
                md=4,
            ),
            dbc.Col(
                _info_card(
                    "Counter-intuitive: warmup may be over-protection",
                    "Strategy A' (no warmup) beats A by +58K BRL — the 3rd-month rule alone provides an implicit warmup.",
                    "warning",
                ),
                md=4,
            ),
            dbc.Col(
                _info_card(
                    "Sanity check passed",
                    "keep_all IT cost = 503,145 BRL ≈ problem statement's 500K cumulative IT cost.",
                    "info",
                ),
                md=4,
            ),
        ]
    ),
])