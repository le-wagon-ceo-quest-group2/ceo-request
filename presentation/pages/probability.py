"""Page: Seller Profitability Analysis"""

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from olist.seller import Seller
from olist.data import Olist

dash.register_page(__name__, path="/profitability", name="Profitability", order=5)

# Data
sellers = Seller().get_training_data()
alpha = 3157.27
beta = 978.23

loss_sellers = sellers[sellers['profits'] < 0]
profitable_sellers = sellers[sellers['profits'] >= 0]

it_cost_current = alpha * np.sqrt(len(sellers)) + beta * np.sqrt(sellers['quantity'].sum())
it_cost_new = alpha * np.sqrt(len(profitable_sellers)) + beta * np.sqrt(profitable_sellers['quantity'].sum())

current_total_profit = sellers['profits'].sum() - it_cost_current
new_total_profit = profitable_sellers['profits'].sum() - it_cost_new

# Single seller orders
order_items = Olist().get_data()['order_items']
total_orders = order_items['order_id'].nunique()
single_seller_orders = order_items.groupby('order_id')['seller_id'].nunique()
single_seller_count = (single_seller_orders == 1).sum()
multi_seller_pct = (1 - single_seller_count / total_orders) * 100

# Waterfall chart
fig = go.Figure(go.Waterfall(
    orientation="v",
    measure=["absolute", "relative", "relative", "relative", "total"],
    x=["Current Profit", "Lost Revenue", "Saved Review Costs", "Saved IT Costs", "New Profit"],
    y=[
        current_total_profit,
        -loss_sellers['revenues'].sum(),
        loss_sellers['cost_of_reviews'].sum(),
        it_cost_current - it_cost_new,
        0
    ],
    connector={"line": {"color": "rgb(63, 63, 63)"}},
    decreasing={"marker": {"color": "red"}},
    increasing={"marker": {"color": "green"}},
    totals={"marker": {"color": "steelblue"}}
))
fig.update_layout(
    title="Impact of Removing Unprofitable Sellers",
    yaxis_title="Profit (BRL)"
)

layout = dbc.Container([
    html.H2("Seller Profitability Analysis"),

    html.Hr(),
    html.H4("Key Metrics"),
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Total Sellers"),
            html.H4(f"{len(sellers)}")
        ])), width=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Unprofitable Sellers"),
            html.H4(f"{len(loss_sellers)}", style={"color": "red"})
        ])), width=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Current Profit (with IT)"),
            html.H4(f"{current_total_profit:,.0f} BRL")
        ])), width=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("New Profit (after removal)"),
            html.H4(f"{new_total_profit:,.0f} BRL", style={"color": "green"})
        ])), width=3),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Current IT Cost"),
            html.H4(f"{it_cost_current:,.0f} BRL")
        ])), width=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("New IT Cost"),
            html.H4(f"{it_cost_new:,.0f} BRL")
        ])), width=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("IT Cost Saving"),
            html.H4(f"{it_cost_current - it_cost_new:,.0f} BRL", style={"color": "green"})
        ])), width=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Profit Difference"),
            html.H4(f"{new_total_profit - current_total_profit:,.0f} BRL", style={"color": "green"})
        ])), width=3),
    ], className="mb-4"),

    html.Hr(),
    dcc.Graph(figure=fig),

    html.Hr(),
    html.H4("Analysis Limitation"),
    dbc.Alert([
        html.P(f"Orders with multiple sellers: {multi_seller_pct:.1f}%"),
        html.P(f"Orders with single seller: {100 - multi_seller_pct:.1f}%"),
        html.P("Since 98.7% of orders have only one seller, the review cost attribution is highly accurate. The assumption that all sellers in an order share the review cost affects less than 1.3% of orders.")
    ], color="warning"),
])
