"""Value-at-Risk utilities."""

from __future__ import annotations

import pandas as pd
from scipy.stats import norm


def historical_var(portfolio_ret: pd.Series, alpha: float) -> tuple[float, float]:
    """Return historical VaR and CVaR for a given alpha."""

    if portfolio_ret.empty:
        raise ValueError("Portfolio return series is empty.")

    var_level = portfolio_ret.quantile(alpha)
    cvar_level = portfolio_ret[portfolio_ret <= var_level].mean()

    return float(-var_level), float(-cvar_level)


def parametric_var(portfolio_ret: pd.Series, alpha: float) -> tuple[float, float]:
    """Return parametric (normal) VaR and CVaR."""

    if portfolio_ret.empty:
        raise ValueError("Portfolio return series is empty.")

    mu = float(portfolio_ret.mean())
    sigma = float(portfolio_ret.std())

    if sigma == 0:
        return float(max(-mu, 0.0)), float(max(-mu, 0.0))

    z_score = norm.ppf(alpha)
    var = -(mu + z_score * sigma)
    cvar = -(mu - sigma * norm.pdf(z_score) / alpha)

    return float(var), float(cvar)
