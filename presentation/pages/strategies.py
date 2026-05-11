"""Page 4: online-strategy designs (A, B, A', C)."""

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

from ._data import load_summary, STRATEGY_DISPLAY, STRATEGY_COLOUR, UPPER_BOUND

dash.register_page(__name__, path="/strategies", name="Strategies", order=4)

summary = load_summary()


def _strategy_card(strategy_key: str, pseudocode: str, why: str):
    row = summary[summary.strategy == strategy_key].iloc[0]
    colour = STRATEGY_COLOUR[strategy_key]
    return dbc.Card(
        [
            dbc.CardHeader(
                STRATEGY_DISPLAY[strategy_key],
                style={"backgroundColor": colour, "color": "white", "fontWeight": "bold"},
            ),
            dbc.CardBody(
                [
                    html.Pre(
                        pseudocode,
                        className="bg-dark text-light p-3 rounded small mb-3",
                        style={"whiteSpace": "pre-wrap"},
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Small("Drops", className="text-muted d-block"),
                                    html.H5(f"{int(row.total_dropped):,}"),
                                ],
                                xs=4,
                            ),
                            dbc.Col(
                                [
                                    html.Small("post-IT (BRL)", className="text-muted d-block"),
                                    html.H5(f"{row.final_post_it_profit:,.0f}"),
                                ],
                                xs=4,
                            ),
                            dbc.Col(
                                [
                                    html.Small("Upper-bound capture", className="text-muted d-block"),
                                    html.H5(f"{row.upper_capture_pct:.1f}%"),
                                ],
                                xs=4,
                            ),
                        ],
                        className="mb-2",
                    ),
                    html.P(why, className="card-text small mb-0"),
                ]
            ),
        ],
        className="h-100",
    )


STRATEGY_A_PSEUDO = """Phase 1 (warmup):  no drops while cum_post_it_profit ≤ 0
Phase 2 (active):  each seller's first 2 months: grace
                   3rd month: run strong-drop test on first-2-mo data
                       v_obs < α(√n − √(n-1)) + β(√Q − √(Q − q_obs))
                   drop on trigger, never re-evaluate"""

STRATEGY_B_PSEUDO = """Phase 1 (warmup):    no drops while cum_post_it_profit ≤ 0
Phase 2 (one shot):  the moment warmup completes, evaluate ALL
                     active sellers in one batch with full history
Phase 3 (passive):   never re-evaluate"""

STRATEGY_A_PRIME_PSEUDO = """No warmup gate. From t = 0:
each month, evaluate any seller whose 3rd active
month is THIS period (same ongoing rule as A)."""

STRATEGY_C_PSEUDO = """Phase 1 (warmup):       no drops while cum_post_it_profit ≤ 0
Phase 2 (first batch):  on warmup completion, evaluate every seller
                        with ≥ 2 months of history (full history each)
Phase 3 (ongoing):      after that, evaluate sellers at their 3rd month
                        as in Strategy A"""

layout = html.Div([
    html.H2("Online strategies"),
    html.P(
        "Four candidates, all using historical data only. Each evaluates sellers "
        "with the closed-form strong-drop test under the current platform state.",
        className="lead",
    ),

    dbc.Row(
        [
            dbc.Col(
                _strategy_card(
                    "A",
                    STRATEGY_A_PSEUDO,
                    "Misses the grandfathered cohort (sellers whose 3rd month falls inside warmup are never evaluated).",
                ),
                md=6,
                className="mb-4",
            ),
            dbc.Col(
                _strategy_card(
                    "B",
                    STRATEGY_B_PSEUDO,
                    "Long observation per seller (5–9 months at warmup completion), but post-warmup onboards are never evaluated.",
                ),
                md=6,
                className="mb-4",
            ),
        ]
    ),

    dbc.Row(
        [
            dbc.Col(
                _strategy_card(
                    "A_prime",
                    STRATEGY_A_PRIME_PSEUDO,
                    "Counter-intuitive: removing warmup beats A by +58K BRL. The 3rd-month rule is itself an implicit warmup.",
                ),
                md=6,
                className="mb-4",
            ),
            dbc.Col(
                _strategy_card(
                    "C",
                    STRATEGY_C_PSEUDO,
                    "Stacks B's long-history first-batch with A's continuous monitoring. Best capture (78%).",
                ),
                md=6,
                className="mb-4",
            ),
        ]
    ),

    html.Hr(),
    html.H4("Evaluation-pool comparison"),
    dbc.Table(
        [
            html.Thead(
                html.Tr(
                    [
                        html.Th(""),
                        html.Th("Initial batch (2017-06)"),
                        html.Th("Subsequent monthly evals"),
                        html.Th("Total evals", style={"textAlign": "right"}),
                        html.Th("Drops", style={"textAlign": "right"}),
                    ]
                )
            ),
            html.Tbody([
                html.Tr([
                    html.Td("A"),
                    html.Td("~118 (onboarded 2017-04 only)"),
                    html.Td("each cohort at 3rd month"),
                    html.Td("~2,225", style={"textAlign": "right"}),
                    html.Td("228", style={"textAlign": "right"}),
                ]),
                html.Tr([
                    html.Td("B"),
                    html.Td("933 (all active)"),
                    html.Td("0 (never re-evaluated)"),
                    html.Td("933", style={"textAlign": "right"}),
                    html.Td("281", style={"textAlign": "right"}),
                ]),
                html.Tr([
                    html.Td("A'"),
                    html.Td("starts 2016-11 with each cohort"),
                    html.Td("every month continuously"),
                    html.Td("~3,000+", style={"textAlign": "right"}),
                    html.Td("445", style={"textAlign": "right"}),
                ]),
                html.Tr([
                    html.Td(html.Strong("C ★")),
                    html.Td("933 (≥ 2 mo history)"),
                    html.Td("each new cohort at 3rd month"),
                    html.Td("~2,640", style={"textAlign": "right"}),
                    html.Td(html.Strong("407"), style={"textAlign": "right"}),
                ]),
            ]),
        ],
        striped=True,
        bordered=True,
        hover=True,
        color="dark",
    ),

    dbc.Alert(
        [
            html.Strong("Forward-only realised P&L: "),
            "all numbers count a dropped seller's pre-drop contributions; only post-drop is excluded. "
            "Matches the online operational reality where realised cash flows cannot be undone.",
        ],
        color="info",
        className="mt-3",
    ),
])