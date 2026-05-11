"""Page 5: per-period trajectory comparison."""

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from ._data import (
    load_all_logs, STRATEGY_ORDER, STRATEGY_DISPLAY, STRATEGY_COLOUR, UPPER_BOUND,
)

dash.register_page(__name__, path="/trajectories", name="Trajectories", order=5)

logs = load_all_logs()


def _line_fig(field, title, ylabel, hline=None):
    fig = go.Figure()
    for name in STRATEGY_ORDER:
        df = logs[name]
        fig.add_trace(
            go.Scatter(
                x=df["period"],
                y=df[field],
                mode="lines+markers",
                name=STRATEGY_DISPLAY[name],
                line=dict(color=STRATEGY_COLOUR[name], width=2),
                marker=dict(size=5),
            )
        )
    if hline is not None:
        fig.add_hline(
            y=hline,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Upper bound: {hline:,.0f}",
            annotation_position="top right",
        )
    fig.update_layout(
        title=title,
        yaxis_title=ylabel,
        template="plotly_dark",
        height=420,
        margin=dict(t=50, l=40, r=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    return fig


cum_post_it_fig = _line_fig(
    "cum_post_it",
    "Cumulative post-IT profit over time",
    "post-IT profit (BRL)",
    hline=UPPER_BOUND,
)

n_active_fig = _line_fig(
    "n_active",
    "Active sellers per month (after drops applied)",
    "sellers",
)

drops_fig = _line_fig(
    "n_dropped_total",
    "Cumulative drops over time",
    "cumulative drops",
)

layout = html.Div([
    html.H2("Trajectory deep-dive"),
    html.P(
        "How each strategy actually unfolds over the 25-month horizon.",
        className="lead",
    ),

    dcc.Graph(figure=cum_post_it_fig),

    dbc.Row(
        [
            dbc.Col(dcc.Graph(figure=n_active_fig), lg=6),
            dbc.Col(dcc.Graph(figure=drops_fig), lg=6),
        ]
    ),

    dbc.Row(
        [
            dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        html.H5("Why C wins", className="card-title"),
                        html.Ul([
                            html.Li("First batch (2017-06): 190 drops from sellers with 5–9 months of history → most accurate evaluations"),
                            html.Li("Ongoing (2017-07 onwards): 217 drops from later cohorts at their 3rd month → catches later deterioration"),
                            html.Li("Neither cohort is permanently grandfathered"),
                        ], className="mb-0"),
                    ])
                ),
                lg=6,
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        html.H5("Why A' didn't collapse", className="card-title"),
                        html.Ul([
                            html.Li("3rd-month rule is itself an implicit warmup — first evaluation only at month 3 of the earliest cohort"),
                            html.Li("By 2016-11 (first eval), platform has grown from 2 to 134 sellers → threshold no longer catastrophic"),
                            html.Li("Even after 83-drop purge at 2016-12, January's 150 new onboards refill the platform"),
                        ], className="mb-0"),
                    ])
                ),
                lg=6,
            ),
        ],
        className="mt-3",
    ),
])