"""Shared data loaders for all presentation pages."""

import os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.normpath(os.path.join(HERE, "..", "cache"))

STRATEGY_ORDER = ["keep_all", "A", "B", "A_prime", "C"]

STRATEGY_DISPLAY = {
    "keep_all": "keep_all",
    "A": "A (warmup + 3rd-month)",
    "B": "B (warmup + one-shot)",
    "A_prime": "A' (no warmup + 3rd-month)",
    "C": "C (hybrid) ★",
}

STRATEGY_COLOUR = {
    "keep_all": "#95A5A6",
    "A": "#5DADE2",
    "B": "#48C9B0",
    "A_prime": "#F4D03F",
    "C": "#27AE60",
}

UPPER_BOUND = 1_089_860


def load_summary():
    df = pd.read_parquet(os.path.join(CACHE, "summary.parquet"))
    df = df.set_index("strategy").loc[STRATEGY_ORDER].reset_index()
    df["display"] = df["strategy"].map(STRATEGY_DISPLAY)
    df["upper_capture_pct"] = (df.final_post_it_profit / UPPER_BOUND * 100).round(1)
    baseline = df.loc[df.strategy == "keep_all", "final_post_it_profit"].iloc[0]
    df["vs_baseline"] = df.final_post_it_profit - baseline
    return df


def load_period_log(strategy: str) -> pd.DataFrame:
    path = os.path.join(CACHE, f"period_log_{strategy}.parquet")
    return pd.read_parquet(path)


def load_all_logs():
    return {name: load_period_log(name) for name in STRATEGY_ORDER}