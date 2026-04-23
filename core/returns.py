"""Return calculations for Risk Lab."""

from __future__ import annotations

import pandas as pd


def compute_returns(prices: pd.DataFrame, frequency: str = "daily") -> pd.DataFrame:
    """Compute percentage returns at the requested frequency."""

    if prices.empty:
        raise ValueError("Price dataframe is empty; cannot compute returns.")

    if frequency not in {"daily", "weekly"}:
        raise ValueError("Frequency must be 'daily' or 'weekly'.")

    if frequency == "weekly":
        prices = prices.resample("W").last()

    return prices.pct_change().dropna(how="all")


def cumulative_returns(returns: pd.Series | pd.DataFrame) -> pd.Series | pd.DataFrame:
    """Compute cumulative return path from simple returns."""

    return (1 + returns).cumprod()
