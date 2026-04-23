"""Performance metrics for Risk Lab."""

from __future__ import annotations

import math
from typing import Dict

import pandas as pd


def portfolio_returns(returns: pd.DataFrame, weights: pd.Series) -> pd.Series:
    """Compute portfolio returns from asset returns and weights."""

    aligned_weights = weights.reindex(returns.columns).fillna(0.0)
    return returns.mul(aligned_weights, axis=1).sum(axis=1)


def performance_metrics(
    portfolio_ret: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> Dict[str, float]:
    """Calculate CAGR, volatility, Sharpe, Sortino, and max drawdown."""

    if portfolio_ret.empty:
        raise ValueError("Portfolio return series is empty.")

    cumulative = (1 + portfolio_ret).prod() - 1
    cagr = (1 + cumulative) ** (periods_per_year / len(portfolio_ret)) - 1

    volatility = portfolio_ret.std() * math.sqrt(periods_per_year)
    downside = portfolio_ret[portfolio_ret < 0].std() * math.sqrt(periods_per_year)
    excess_return = cagr - risk_free_rate

    sharpe = excess_return / volatility if volatility > 0 else 0.0
    sortino = excess_return / downside if downside > 0 else 0.0

    cumulative_curve = (1 + portfolio_ret).cumprod()
    running_max = cumulative_curve.cummax()
    drawdown = (cumulative_curve / running_max) - 1
    max_drawdown = float(drawdown.min())

    return {
        "CAGR": float(cagr),
        "Annual Volatility": float(volatility),
        "Sharpe": float(sharpe),
        "Sortino": float(sortino),
        "Max Drawdown": max_drawdown,
    }


def drawdown_curve(portfolio_ret: pd.Series) -> pd.Series:
    """Return drawdown series from a portfolio return series."""

    cumulative_curve = (1 + portfolio_ret).cumprod()
    running_max = cumulative_curve.cummax()
    return (cumulative_curve / running_max) - 1
