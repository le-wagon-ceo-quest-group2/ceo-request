"""Optimum seller-subset solvers for the Olist CEO-request what-if analysis.

Maximise over a subset S of sellers:

    profit(S) = sum_{i in S} v_i - alpha * sqrt(|S|) - beta * sqrt(sum_{i in S} q_i)

where v_i = pre-IT profit of seller i, q_i = items sold.

Public API
----------
* solve_lagrangian   — KKT fixed-point. Milliseconds. Continuous-relaxation optimum.
* solve_misocp       — Mixed-Integer SOCP via CVXPY. Strict integer optimum, slow.
* refine_local_swap  — Single-bit-flip refinement on any candidate mask.
* total_profit       — Evaluate a mask.
* it_cost            — IT cost given n_sellers and n_items.
* summarise          — One-row DataFrame summary of a solution.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

ALPHA_DEFAULT = 3157.27
BETA_DEFAULT = 978.23

PROFIT_COL_DEFAULT = "pre_it_profits"
QTY_COL_DEFAULT = "quantity"


# --------------------------------------------------------------------------- #
# Utilities
# --------------------------------------------------------------------------- #

def it_cost(n_sellers, n_items, alpha=ALPHA_DEFAULT, beta=BETA_DEFAULT):
    """Cumulated IT cost for a given platform size."""
    return alpha * np.sqrt(n_sellers) + beta * np.sqrt(n_items)


def total_profit(keep, v, q, alpha=ALPHA_DEFAULT, beta=BETA_DEFAULT):
    """Post-IT profit of the subset indicated by boolean mask `keep`."""
    keep = np.asarray(keep, dtype=bool)
    if not keep.any():
        return 0.0
    n = int(keep.sum())
    items = float(q[keep].sum())
    return float(v[keep].sum() - it_cost(n, items, alpha, beta))


def _extract_v_q(sellers, profit_col, qty_col):
    """Accept either a DataFrame or a (v, q) tuple of arrays."""
    if isinstance(sellers, pd.DataFrame):
        return sellers[profit_col].to_numpy(), sellers[qty_col].to_numpy()
    v, q = sellers
    return np.asarray(v, dtype=float), np.asarray(q, dtype=float)


# --------------------------------------------------------------------------- #
# Solver 1: Lagrangian fixed point
# --------------------------------------------------------------------------- #

def solve_lagrangian(
    sellers,
    alpha=ALPHA_DEFAULT,
    beta=BETA_DEFAULT,
    max_iter=200,
    profit_col=PROFIT_COL_DEFAULT,
    qty_col=QTY_COL_DEFAULT,
):
    """KKT fixed-point iteration.

    At the KKT point, seller i is kept iff
        v_i > alpha / (2 sqrt(n*)) + beta * q_i / (2 sqrt(I*))

    Iterate (n_hat, I_hat) until the kept set stabilises.

    Returns
    -------
    keep : np.ndarray of bool, shape (N,)
        True for sellers in the optimal subset.
    """
    v, q = _extract_v_q(sellers, profit_col, qty_col)

    keep = np.ones_like(v, dtype=bool)
    n_hat = int(keep.sum())
    I_hat = float(q[keep].sum())

    for _ in range(max_iter):
        fixed = alpha / (2 * np.sqrt(max(n_hat, 1)))
        rate = beta / (2 * np.sqrt(max(I_hat, 1.0)))
        new_keep = v > fixed + rate * q

        new_n = int(new_keep.sum())
        new_I = float(q[new_keep].sum())

        if (new_n, new_I) == (n_hat, I_hat):
            keep = new_keep
            break
        keep, n_hat, I_hat = new_keep, new_n, new_I

    return keep


# --------------------------------------------------------------------------- #
# Solver 2: Mixed-Integer SOCP
# --------------------------------------------------------------------------- #

def solve_misocp(
    sellers,
    alpha=ALPHA_DEFAULT,
    beta=BETA_DEFAULT,
    solver=None,
    verbose=False,
    profit_col=PROFIT_COL_DEFAULT,
    qty_col=QTY_COL_DEFAULT,
):
    """Strict-integer optimum via Mixed-Integer SOCP.

    Formulation:
        max  v^T x - alpha * sn - beta * sI
        s.t. sn >= sqrt(1^T x)         (SOC)
             sI >= sqrt(q^T x)         (SOC)
             x in {0, 1}^N

    Requires a MIP-capable solver (MOSEK, GUROBI, SCIP). Pass via `solver=`.

    Returns
    -------
    keep : np.ndarray of bool, shape (N,)
    """
    import cvxpy as cp

    v, q = _extract_v_q(sellers, profit_col, qty_col)
    if (q < 0).any():
        raise ValueError("quantity must be non-negative")
    N = len(v)
    sqrt_q = np.sqrt(q)

    x = cp.Variable(N, boolean=True)
    sn = cp.Variable(nonneg=True)
    sI = cp.Variable(nonneg=True)

    objective = cp.Maximize(v @ x - alpha * sn - beta * sI)
    # Boolean trick: x_i^2 = x_i, hence
    #   sqrt(sum(x))   == ||x||_2
    #   sqrt(q^T x)    == ||sqrt(q) * x||_2  (q >= 0)
    # Using cp.norm keeps both as standard SOC constraints, DCP-compliant.
    constraints = [
        sn >= cp.norm(x, 2),
        sI >= cp.norm(cp.multiply(sqrt_q, x), 2),
    ]

    prob = cp.Problem(objective, constraints)
    prob.solve(solver=solver, verbose=verbose)

    if x.value is None:
        raise RuntimeError(
            f"MISOCP solver did not return a solution (status={prob.status})"
        )

    return x.value > 0.5


# --------------------------------------------------------------------------- #
# Local refinement
# --------------------------------------------------------------------------- #

def refine_local_swap(
    keep,
    sellers,
    alpha=ALPHA_DEFAULT,
    beta=BETA_DEFAULT,
    max_passes=10,
    profit_col=PROFIT_COL_DEFAULT,
    qty_col=QTY_COL_DEFAULT,
):
    """Iterative single-bit-flip improvement.

    On each pass, flip every seller's status one at a time and keep the flip
    if profit strictly improves. Stop when a full pass yields no improvement.
    """
    v, q = _extract_v_q(sellers, profit_col, qty_col)
    keep = np.asarray(keep, dtype=bool).copy()

    cur = total_profit(keep, v, q, alpha, beta)

    for _ in range(max_passes):
        improved = False
        for i in range(len(keep)):
            keep[i] = not keep[i]
            new = total_profit(keep, v, q, alpha, beta)
            if new > cur + 1e-6:
                cur = new
                improved = True
            else:
                keep[i] = not keep[i]
        if not improved:
            break

    return keep


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #

def summarise(
    keep,
    sellers,
    alpha=ALPHA_DEFAULT,
    beta=BETA_DEFAULT,
    label=None,
    profit_col=PROFIT_COL_DEFAULT,
    qty_col=QTY_COL_DEFAULT,
):
    """One-row DataFrame summarising a candidate solution."""
    v, q = _extract_v_q(sellers, profit_col, qty_col)
    keep = np.asarray(keep, dtype=bool)
    n = int(keep.sum())
    items = float(q[keep].sum())
    pre = float(v[keep].sum())
    cost = it_cost(n, items, alpha, beta) if n else 0.0
    row = {
        "n_kept": n,
        "n_total": len(keep),
        "items_kept": items,
        "pre_it_profit": pre,
        "it_cost": cost,
        "post_it_profit": pre - cost,
    }
    if label is not None:
        row = {"method": label, **row}
    return pd.DataFrame([row])
