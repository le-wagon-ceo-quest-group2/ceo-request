"""Olist CEO Request — presentation web app.

Run:
    python presentation/main.py
Then open http://127.0.0.1:8050 in a browser.

Prereq: run `python presentation/build_results.py` once to cache strategy
results before starting the app.
"""

import dash
from dash import Dash, html
import dash_bootstrap_components as dbc

app = Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.SLATE, dbc.icons.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="Olist CEO Request",
)

navbar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(
            dbc.NavLink(page["name"], href=page["relative_path"], active="exact")
        )
        for page in sorted(dash.page_registry.values(), key=lambda p: p.get("order", 99))
    ],
    brand="Olist CEO Request — Should we remove under-performing sellers?",
    brand_href="/",
    color="dark",
    dark=True,
    sticky="top",
)

app.layout = html.Div([
    navbar,
    dbc.Container(dash.page_container, fluid=True, className="py-4 px-5"),
])

if __name__ == "__main__":
    app.run(debug=True, port=8050)
