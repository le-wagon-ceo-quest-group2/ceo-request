"""Page 0: presentation cover."""

import dash
from dash import html
import dash_bootstrap_components as dbc

dash.register_page(__name__, path="/", name="Cover", order=-1)


def _member(name: str, accent: str):
    return dbc.Card(
        dbc.CardBody([
            html.Div(
                html.I(className="bi bi-person-fill"),
                style={
                    "fontSize": "3rem",
                    "color": accent,
                    "textAlign": "center",
                },
                className="mb-2",
            ),
            html.H4(name, className="text-center mb-0"),
        ]),
        className="h-100",
        style={"backgroundColor": "rgba(255, 255, 255, 0.05)", "border": "1px solid rgba(255, 255, 255, 0.1)"},
    )


layout = html.Div(
    [
        # Top spacer
        html.Div(style={"height": "8vh"}),

        # Hero block
        html.Div(
            [
                html.Div(
                    "Le Wagon · Decision Science",
                    className="text-uppercase text-info mb-3",
                    style={"letterSpacing": "0.3rem", "fontSize": "0.9rem"},
                ),
                html.H1(
                    "CEO Request",
                    className="display-1 fw-bold mb-3",
                    style={"letterSpacing": "-0.02em"},
                ),
                html.H3(
                    "Should we remove under-performing sellers?",
                    className="text-secondary fst-italic",
                    style={"fontWeight": 300},
                ),
            ],
            className="text-center mb-5",
        ),

        # Members
        dbc.Container(
            [
                html.H4(
                    "Research Group 2",
                    className="text-center text-warning mb-4",
                    style={"letterSpacing": "0.2rem"},
                ),
                dbc.Row(
                    [
                        dbc.Col(_member("Hang", "#5DADE2"), md=4, className="mb-3"),
                        dbc.Col(_member("Mario", "#48C9B0"), md=4, className="mb-3"),
                        dbc.Col(_member("Soodabeh", "#F4D03F"), md=4, className="mb-3"),
                    ],
                    justify="center",
                ),
            ],
            style={"maxWidth": "720px"},
        ),

        # Footer hint
        html.Div(
            html.P(
                "→ navigate via the menu above, or start at TL;DR",
                className="text-muted text-center mt-5 fst-italic",
            ),
            style={"opacity": 0.7},
        ),
    ],
    style={"minHeight": "75vh"},
)
