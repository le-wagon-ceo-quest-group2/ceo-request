"""Strong must-keep / must-drop sets for the Olist seller selection problem.

Computes provably correct subsets of K (sellers in every global optimum) and
D (sellers in no global optimum), without solving any MISOCP.

Two functions:

* closed_form_strong_sets — single-pass O(N) using the extreme cases
                            S = empty (worst case for K test) and
                            S = full \\ {i} (best case for D test).
* propagate_strong_sets   — iterative constraint propagation that tightens the
                            bounds round by round. Whatever closed-form decides,
                            propagation will decide at least as much; usually
                            substantially more.

Both return boolean arrays. Sellers not in K nor D are "undecided" — they may
or may not appear in particular global optima (the swing set).

Helpers:

* summarise_sets — one-row DataFrame summary of a (K, D) decomposition.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

ALPHA_DEFAULT = 3157.27
BETA_DEFAULT = 978.23

PROFIT_COL_DEFAULT = "pre_it_profits"
QTY_COL_DEFAULT = "quantity"


# --------------------------------------------------------------------------- #
# Closed-form
# --------------------------------------------------------------------------- #

def closed_form_strong_sets(
    sellers,
    alpha=ALPHA_DEFAULT,
    beta=BETA_DEFAULT,
    profit_col=PROFIT_COL_DEFAULT,
    qty_col=QTY_COL_DEFAULT,
):
    """One-pass O(N) computation.

    Strong-keep test (S = empty, the worst-case marginal):
        v_i > alpha + beta * sqrt(q_i)

    Strong-drop test (S = full \\ {i}, the best-case marginal):
        v_i < alpha * (sqrt(N) - sqrt(N - 1))
              + beta * (sqrt(Q_tot) - sqrt(Q_tot - q_i))

    Returns
    -------
    (K_plus, D_plus) : tuple of np.ndarray of bool, both shape (N,)
    """
    v = sellers[profit_col].to_numpy(dtype=float)
    q = sellers[qty_col].to_numpy(dtype=float)
    N = len(sellers)
    Q_tot = float(q.sum())

    # K_plus
    K_plus = v > alpha + beta * np.sqrt(q)

    # D_plus
    if N > 1:
        fixed_term = alpha * (np.sqrt(N) - np.sqrt(N - 1))
    else:
        fixed_term = alpha  # degenerate single-seller case

    safe_qsmax = np.maximum(Q_tot - q, 0.0)
    var_term = beta * (np.sqrt(Q_tot) - np.sqrt(safe_qsmax))
    D_plus = v < fixed_term + var_term

    return K_plus, D_plus


# --------------------------------------------------------------------------- #
# Iterative propagation
# --------------------------------------------------------------------------- #

def propagate_strong_sets(
    sellers,
    alpha=ALPHA_DEFAULT,
    beta=BETA_DEFAULT,
    max_iter=50,
    profit_col=PROFIT_COL_DEFAULT,
    qty_col=QTY_COL_DEFAULT,
    verbose=False,
):
    """Fixed-point propagation that tightens (K, D) iteratively.

    Each round uses current (K, D) to bound any optimum's |S| and Q_S, then
    re-tests every undecided seller using the tightened bounds. Stops when no
    seller is added.

    Theoretically, K and D returned here are still subsets of the true
    intersection sets (sound but not complete); empirically they capture the
    vast majority because the bounds tighten monotonically.

    Returns
    -------
    K, D : np.ndarray of bool, shape (N,)
    history : list of dict with per-iteration counts
    """
    v = sellers[profit_col].to_numpy(dtype=float)
    q = sellers[qty_col].to_numpy(dtype=float)
    N = len(sellers)

    K = np.zeros(N, dtype=bool)
    D = np.zeros(N, dtype=bool)
    history = []

    for it in range(max_iter):
        n_lo = int(K.sum())
        n_hi = N - int(D.sum())
        Q_lo = float(q[K].sum())
        Q_hi = float(q[~D].sum())

        undecided = ~(K | D)
        und_idx = np.where(undecided)[0]

        if len(und_idx) == 0:
            history.append({
                "iter": it, "added_K": 0, "added_D": 0,
                "total_K": int(K.sum()), "total_D": int(D.sum()),
                "undecided": 0,
            })
            break

        # ---- K test -----------------------------------------------------
        # Min Delta_i achieved at S = K (smallest |S| and Q_S)
        # Need n_lo + 1 <= n_hi for the seller to fit
        if n_lo < n_hi:
            fixed_marg_max = alpha * (np.sqrt(n_lo + 1) - np.sqrt(n_lo))
            var_marg_max = beta * (
                np.sqrt(Q_lo + q[und_idx]) - np.sqrt(Q_lo)
            )
            min_delta = v[und_idx] - fixed_marg_max - var_marg_max
            new_K_mask = min_delta > 0
        else:
            new_K_mask = np.zeros(len(und_idx), dtype=bool)

        new_K_idx = und_idx[new_K_mask]

        # ---- D test (exclude sellers just added to K) -------------------
        rest = und_idx[~new_K_mask]

        if n_hi >= 1 and len(rest) > 0:
            fixed_marg_min = alpha * (np.sqrt(n_hi) - np.sqrt(n_hi - 1))
            qsmax = Q_hi - q[rest]
            # Numerically guard non-negative argument to sqrt
            qsmax_safe = np.maximum(qsmax, 0.0)
            var_marg_min = beta * (
                np.sqrt(Q_hi) - np.sqrt(qsmax_safe)
            )
            max_delta = v[rest] - fixed_marg_min - var_marg_min
            new_D_mask = max_delta < 0
            new_D_idx = rest[new_D_mask]
        else:
            new_D_idx = np.array([], dtype=int)

        added_K = len(new_K_idx)
        added_D = len(new_D_idx)

        history.append({
            "iter": it,
            "added_K": added_K,
            "added_D": added_D,
            "total_K": int(K.sum()) + added_K,
            "total_D": int(D.sum()) + added_D,
            "undecided": int(undecided.sum()) - added_K - added_D,
        })

        if verbose:
            print(
                f"iter {it:>2}: +K={added_K:>4}  +D={added_D:>4}  "
                f"|K|={int(K.sum()) + added_K:>4}  "
                f"|D|={int(D.sum()) + added_D:>4}  "
                f"undecided={int(undecided.sum()) - added_K - added_D:>4}"
            )

        if added_K == 0 and added_D == 0:
            break

        K[new_K_idx] = True
        D[new_D_idx] = True

    return K, D, history


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #

def summarise_sets(
    K,
    D,
    sellers,
    profit_col=PROFIT_COL_DEFAULT,
    qty_col=QTY_COL_DEFAULT,
    label=None,
):
    """One-row DataFrame summarising a (K, D) decomposition."""
    K = np.asarray(K, dtype=bool)
    D = np.asarray(D, dtype=bool)
    N = len(sellers)
    n_K = int(K.sum())
    n_D = int(D.sum())
    n_W = N - n_K - n_D
    row = {
        "n_total": N,
        "n_strong_keep": n_K,
        "n_strong_drop": n_D,
        "n_swing": n_W,
        "profit_keep_sum": float(sellers.loc[K, profit_col].sum()) if n_K else 0.0,
        "profit_drop_sum": float(sellers.loc[D, profit_col].sum()) if n_D else 0.0,
        "items_keep_sum": float(sellers.loc[K, qty_col].sum()) if n_K else 0.0,
        "items_drop_sum": float(sellers.loc[D, qty_col].sum()) if n_D else 0.0,
    }
    if label is not None:
        row = {"method": label, **row}
    return pd.DataFrame([row])


# --------------------------------------------------------------------------- #
# Demo
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    # Self-test on synthetic data so the file is runnable without the dataset
    rng = np.random.default_rng(0)
    N = 2000
    df = pd.DataFrame({
        PROFIT_COL_DEFAULT: rng.normal(0, 200, N),
        QTY_COL_DEFAULT: (rng.lognormal(2, 1, N) + 1).astype(float),
    })

    print("Synthetic dataset:", df.shape)
    print(df.describe(), "\n")

    K1, D1 = closed_form_strong_sets(df)
    print("Closed-form:")
    print(summarise_sets(K1, D1, df, label="closed_form").to_string(index=False))
    print()

    K2, D2, hist = propagate_strong_sets(df, verbose=True)
    print("\nPropagated:")
    print(summarise_sets(K2, D2, df, label="propagated").to_string(index=False))
