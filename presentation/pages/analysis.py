"""Page: Sales & Negative Reviews by Brazilian State.

Adapted from Mario's standalone analysis notebook into a Dash page. Loads raw
Olist CSVs and computes state-level aggregates inline (no `bi_data` dependency).
"""

import os
import sys

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.express as px

# Ensure the local `olist` package is importable
_HERE = os.path.dirname(os.path.abspath(__file__))
_DECISION_SCIENCE = os.path.normpath(os.path.join(_HERE, "..", "..", "..", ".."))
if _DECISION_SCIENCE not in sys.path:
    sys.path.insert(0, _DECISION_SCIENCE)

dash.register_page(__name__, path="/analysis", name="State Analysis", order=4)

DATA_DIR = os.path.expanduser("~/.lewagon/olist/data/csv")


# --------------------------------------------------------------------------- #
# Load raw data
# --------------------------------------------------------------------------- #

def _load_state_data():
    orders = pd.read_csv(
        f"{DATA_DIR}/olist_orders_dataset.csv",
        usecols=["order_id", "customer_id", "order_status"],
    )
    customers = pd.read_csv(
        f"{DATA_DIR}/olist_customers_dataset.csv",
        usecols=["customer_id", "customer_state"],
    )
    items = pd.read_csv(
        f"{DATA_DIR}/olist_order_items_dataset.csv",
        usecols=["order_id", "price", "freight_value"],
    )
    reviews = pd.read_csv(
        f"{DATA_DIR}/olist_order_reviews_dataset.csv",
        usecols=["order_id", "review_score"],
    )

    orders_kept = orders[~orders.order_status.isin(("canceled", "unavailable"))]
    order_state = orders_kept.merge(customers, on="customer_id", how="inner")[
        ["order_id", "customer_state"]
    ]

    # Per-state sales total (price-only, no freight, consistent with Olist convention)
    items_by_order = items.groupby("order_id", as_index=False)["price"].sum()
    sales_per_order = order_state.merge(items_by_order, on="order_id", how="inner")
    state_sales = (
        sales_per_order.groupby("customer_state", as_index=False)["price"]
        .sum()
        .rename(columns={"price": "sales"})
        .sort_values("sales", ascending=False)
    )
    state_sales["sales_pct"] = state_sales["sales"] / state_sales["sales"].sum() * 100

    # Per-state review aggregates (negative = score ≤ 3)
    reviews_state = reviews.merge(order_state, on="order_id", how="inner")
    reviews_state["is_negative"] = reviews_state["review_score"] <= 3
    review_by_state = (
        reviews_state.groupby("customer_state", as_index=False)
        .agg(
            total_reviews=("review_score", "count"),
            negative_reviews=("is_negative", "sum"),
        )
    )
    review_by_state["negative_review_pct"] = (
        review_by_state["negative_reviews"] / review_by_state["total_reviews"] * 100
    ).round(2)

    state = state_sales.merge(review_by_state, on="customer_state", how="left")
    return state


state = _load_state_data()
avg_neg = state["negative_review_pct"].mean()


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #

# Top-10 bar
fig_top10 = px.bar(
    state.head(10),
    x="customer_state",
    y="sales",
    color="sales",
    color_continuous_scale="Blues",
    title="Top 10 states by total sales",
    labels={"customer_state": "State", "sales": "Sales (BRL)"},
    template="plotly_dark",
)
fig_top10.update_layout(height=420, coloraxis_showscale=False)

# All states horizontal
fig_all = px.bar(
    state.sort_values("sales", ascending=True),
    x="sales",
    y="customer_state",
    orientation="h",
    color="sales",
    color_continuous_scale="Blues",
    title="Sales revenue by customer state (all)",
    labels={"customer_state": "State", "sales": "Sales (BRL)"},
    template="plotly_dark",
)
fig_all.update_layout(height=700, coloraxis_showscale=False)

# Cumulative concentration
state_sorted = state.sort_values("sales", ascending=False).reset_index(drop=True)
state_sorted["cum_pct"] = state_sorted["sales_pct"].cumsum()
fig_cum = px.line(
    state_sorted,
    x="customer_state",
    y="cum_pct",
    markers=True,
    title="Cumulative share of sales by state (sorted)",
    labels={"customer_state": "State", "cum_pct": "Cumulative share (%)"},
    template="plotly_dark",
)
fig_cum.add_hline(
    y=80,
    line_dash="dash",
    line_color="red",
    annotation_text="80% of sales",
    annotation_position="bottom right",
)
fig_cum.update_layout(height=400)

# Sales vs negative review scatter
fig_scatter = px.scatter(
    state,
    x="sales_pct",
    y="negative_review_pct",
    size="total_reviews",
    color="negative_review_pct",
    color_continuous_scale="RdYlGn_r",
    hover_name="customer_state",
    text="customer_state",
    title="Sales share vs negative review rate per state",
    labels={
        "sales_pct": "Sales share (%)",
        "negative_review_pct": "Negative review rate (%)",
        "total_reviews": "# reviews",
    },
    template="plotly_dark",
)
fig_scatter.add_hline(
    y=avg_neg,
    line_dash="dash",
    line_color="white",
    annotation_text=f"avg = {avg_neg:.1f}%",
    annotation_position="top right",
)
fig_scatter.update_traces(textposition="top center")
fig_scatter.update_layout(height=500)


# Brazil choropleth (best-effort: requires internet for the geojson)
fig_map = None
try:
    import requests

    geojson_url = (
        "https://raw.githubusercontent.com/codeforamerica/click_that_hood/"
        "master/public/data/brazil-states.geojson"
    )
    brazil_geo = requests.get(geojson_url, timeout=5).json()
    fig_map = px.choropleth(
        state,
        geojson=brazil_geo,
        locations="customer_state",
        featureidkey="properties.sigla",
        color="sales",
        color_continuous_scale="Blues",
        title="Olist sales by Brazilian state",
        labels={"sales": "Sales (BRL)"},
        hover_name="customer_state",
        hover_data={"sales": ":,.0f", "sales_pct": ":.1f"},
    )
    fig_map.update_geos(
        center=dict(lat=-14.2, lon=-51.9),
        projection_scale=4.5,
        showcountries=True,
        showcoastlines=True,
    )
    fig_map.update_layout(
        height=600,
        template="plotly_dark",
        margin={"r": 0, "t": 60, "l": 0, "b": 0},
    )
except Exception:
    pass  # we'll just omit the map if offline


# Risky states: low sales share, high negative review rate
risky = state[
    (state["sales_pct"] < 2) & (state["negative_review_pct"] > avg_neg)
].sort_values("negative_review_pct", ascending=False)


# --------------------------------------------------------------------------- #
# Layout
# --------------------------------------------------------------------------- #

def _risky_table():
    rows = [
        html.Tr([
            html.Td(r["customer_state"]),
            html.Td(f"{r['sales']:,.0f}", style={"textAlign": "right"}),
            html.Td(f"{r['sales_pct']:.2f}%", style={"textAlign": "right"}),
            html.Td(f"{r['negative_review_pct']:.1f}%", style={"textAlign": "right"}),
            html.Td(f"{int(r['total_reviews']):,}", style={"textAlign": "right"}),
        ])
        for _, r in risky.iterrows()
    ]
    return dbc.Table(
        [
            html.Thead(html.Tr([
                html.Th("State"),
                html.Th("Sales (BRL)", style={"textAlign": "right"}),
                html.Th("Sales share", style={"textAlign": "right"}),
                html.Th("Negative review %", style={"textAlign": "right"}),
                html.Th("Reviews", style={"textAlign": "right"}),
            ])),
            html.Tbody(rows),
        ],
        striped=True,
        bordered=True,
        hover=True,
        color="dark",
        responsive=True,
    )


map_block = (
    [html.H3("Geographic distribution"), dcc.Graph(figure=fig_map), html.Hr()]
    if fig_map is not None
    else []
)

layout = html.Div([
    html.H2("Sales & Negative Reviews by Brazilian State"),
    html.P(
        "Where is Olist's revenue concentrated, and where are customers least satisfied? "
        "Adapted from Mario's analysis notebook.",
        className="lead",
    ),

    dbc.Row(
        [
            dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        html.H6("Total states", className="text-muted"),
                        html.H3(f"{len(state)}"),
                    ])
                ),
                md=3,
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        html.H6("Top-1 state share", className="text-muted"),
                        html.H3(f"{state['sales_pct'].iloc[0]:.1f}%"),
                        html.Small(state["customer_state"].iloc[0], className="text-info"),
                    ])
                ),
                md=3,
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        html.H6("Avg negative review rate", className="text-muted"),
                        html.H3(f"{avg_neg:.1f}%"),
                    ])
                ),
                md=3,
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        html.H6("Risky states (low sales, high neg %)", className="text-muted"),
                        html.H3(f"{len(risky)}", className="text-warning"),
                    ])
                ),
                md=3,
            ),
        ],
        className="mb-4",
    ),

    html.H3("Concentration"),
    dbc.Row(
        [
            dbc.Col(dcc.Graph(figure=fig_top10), lg=6),
            dbc.Col(dcc.Graph(figure=fig_cum), lg=6),
        ]
    ),
    dcc.Graph(figure=fig_all),
    html.Hr(),

    *map_block,

    html.H3("Negative reviews vs sales share"),
    dcc.Graph(figure=fig_scatter),
    html.P(
        "States in the upper-left (low sales share, high negative review rate) are the reputational risks "
        "— little revenue to lose, but disproportionate damage to brand.",
        className="text-muted",
    ),
    html.Hr(),

    html.H3("Risky states (sales share < 2% AND above-average negative rate)"),
    _risky_table(),

    dbc.Alert(
        [
            html.H5("Insight", className="alert-heading"),
            html.P([
                "Several Brazilian states generate very low revenue for Olist while producing ",
                html.Strong("above-average negative reviews"),
                ". These states are a reputational risk with limited financial upside — "
                "investigate the root causes of poor customer experience there to protect the brand.",
            ], className="mb-0"),
        ],
        color="warning",
        className="mt-3",
    ),
])
