"""Page 6: takeaways and further directions."""

import dash
from dash import html
import dash_bootstrap_components as dbc

dash.register_page(__name__, path="/takeaways", name="Takeaways", order=6)


def _takeaway(num, title, body, colour="info"):
    return dbc.Card(
        dbc.CardBody([
            html.Div([
                dbc.Badge(f"{num}", color=colour, className="me-2 fs-4"),
                html.Strong(title, className="fs-5"),
            ], className="mb-2"),
            html.P(body, className="card-text mb-0"),
        ]),
        className="mb-3",
    )


layout = html.Div([
    html.H2("Takeaways"),
    html.P("Six lessons from this study.", className="lead"),

    _takeaway(
        1,
        "Hybrid beats single-policy strategies",
        "C combines A's continuous monitoring with B's long-history first batch and beats both by 56–115K BRL. The two policies cover complementary cohorts; combining resolves both blind spots.",
        "success",
    ),
    _takeaway(
        2,
        "Longer observation windows are more accurate",
        "C's first batch uses 5–9 months of history and judges well; ongoing falls back to 2 months and loses accuracy. Natural next experiment: extend ongoing's window.",
        "info",
    ),
    _takeaway(
        3,
        "A and B have complementary blind spots",
        "A's '3rd month + warmup' rule misses sellers onboarded before warmup_period − 2. B's 'one-shot at warmup' rule misses sellers onboarded after warmup. C stitches both rules together so no seller is permanently exempt.",
        "info",
    ),
    _takeaway(
        4,
        "Warmup protection may not be necessary",
        "A' without warmup still delivers +21% over baseline, +58K BRL over A. The 3rd-month rule is itself an implicit warmup (no seller is evaluated in the first 2 months). Caveat: this is strongly data-dependent — Olist's 100%+ early growth saved A'.",
        "warning",
    ),
    _takeaway(
        5,
        "Limits of weakened strong-drop in an online setting",
        "The closed-form strong-drop test only flags sellers who lose money under any environment. Real data has many sellers who are marginally profitable but inflate IT cost — strong-drop misses these. A tighter criterion (true KKT threshold, marginal contribution) would help.",
        "warning",
    ),
    _takeaway(
        6,
        "Accounting conventions must be strict",
        "Calendar-months × 80 differs from Olist's days/30 convention by ~17%. Combined with dense-panel ghost rows and retroactive-vs-forward-only confusion, three bugs together could make a mediocre strategy report 97% capture (fake). Step one for any backtest: reconcile keep_all and verify IT cost ≈ 500K BRL.",
        "danger",
    ),

    html.Hr(),
    html.H2("Further research directions"),
    dbc.Row(
        [
            dbc.Col(
                dbc.Card(dbc.CardBody([
                    html.H5("Algorithmic"),
                    html.Ul([
                        html.Li("Multi-window comparison: A with windows = 1, 2, 4, 6, 12 mo"),
                        html.Li("Two-stage: B's one-shot + 6-month re-evaluation"),
                        html.Li("Threshold safety factor c < 1"),
                        html.Li("Lifetime extrapolation from observed months"),
                        html.Li("Beta-Binomial posterior on bad-review rate"),
                    ]),
                ])),
                lg=6,
            ),
            dbc.Col(
                dbc.Card(dbc.CardBody([
                    html.H5("Methodological"),
                    html.Ul([
                        html.Li("NLP signals from review_comment_message"),
                        html.Li("Causal analysis (wait_time → review): IV / matching"),
                        html.Li("Tighter oracle that also chooses when to drop"),
                        html.Li("Validate strategy on a slow-growth synthetic dataset"),
                    ]),
                ])),
                lg=6,
            ),
        ],
        className="mb-4",
    ),

    dbc.Alert(
        [
            html.H4("Recommendation to CEO", className="alert-heading"),
            html.P([
                "Deploy ",
                html.Strong("Strategy C (hybrid)"),
                " as the seller-retention policy. Expected annual uplift: ",
                html.Strong("+29% net profit vs status quo"),
                ", or +193K BRL over the historical horizon.",
            ]),
            html.Hr(),
            html.P(
                "Operationally simple: (1) run a one-shot evaluation of all current "
                "sellers; (2) thereafter, evaluate each new seller at their 3rd active "
                "month. No ML model required; closed-form rule.",
                className="mb-0",
            ),
        ],
        color="success",
        className="mt-3",
    ),
])
