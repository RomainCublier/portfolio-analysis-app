"""
Multi-factor model with ETF-based factor proxies.

Factors
-------
MKT   : Market excess return  (SPY – Rf)
SMB   : Small minus Big       (IWM – IWB)
HML   : High minus Low Value  (IWD – IWF)
MOM   : Momentum              (MTUM)

Regression outputs alpha, betas, R², t-stats, idiosyncratic vol.
"""

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta


FACTOR_MAP = {
    "MKT_GROSS": "SPY",
    "SMALL":     "IWM",
    "LARGE":     "IWB",
    "VALUE":     "IWD",
    "GROWTH":    "IWF",
    "MOM":       "MTUM",
}


def _dl(tickers: list, start: str, end: str) -> pd.DataFrame:
    raw = yf.download(tickers, start=start, end=end,
                      auto_adjust=True, progress=False)
    if raw.empty:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"]
        if isinstance(prices, pd.Series):
            prices = prices.to_frame(name=tickers[0])
    else:
        prices = raw[["Close"]].copy()
        prices.columns = [tickers[0]]
    return prices.dropna(how="all")


def get_factors(start: str, end: str, rf_annual: float = 0.04) -> pd.DataFrame:
    """
    Download factor proxy prices and compute daily factor returns.
    Returns a DataFrame with columns [MKT, SMB, HML, MOM] (daily, not excess).
    """
    tickers = list(set(FACTOR_MAP.values()))
    raw  = yf.download(tickers, start=start, end=end,
                       auto_adjust=True, progress=False)
    if raw.empty:
        return pd.DataFrame()

    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"]
    else:
        prices = raw

    rets     = prices.pct_change().dropna()
    rf_daily = rf_annual / 252
    factors  = pd.DataFrame(index=rets.index)

    # Market excess return
    if "SPY" in rets.columns:
        factors["MKT"] = rets["SPY"] - rf_daily

    # Size factor: small-cap – large-cap
    if "IWM" in rets.columns and "IWB" in rets.columns:
        factors["SMB"] = rets["IWM"] - rets["IWB"]

    # Value factor: value – growth
    if "IWD" in rets.columns and "IWF" in rets.columns:
        factors["HML"] = rets["IWD"] - rets["IWF"]

    # Momentum factor
    if "MTUM" in rets.columns:
        factors["MOM"] = rets["MTUM"]

    return factors.dropna()


def factor_regression(
    asset_returns: pd.Series,
    factors: pd.DataFrame,
    rf_daily: float = 0.04 / 252,
) -> dict:
    """
    OLS regression of asset excess returns on factors.

    Returns
    -------
    dict with keys:
        alpha_ann   : Jensen's alpha (annualised)
        betas       : dict {factor_name: beta}
        t_stats     : dict {factor_name: t-stat}  (incl. alpha)
        r_squared   : float
        adj_r2      : float
        idio_vol    : annualised idiosyncratic volatility
        residuals   : pd.Series
        factor_rets : monthly factor contribution breakdown
    """
    excess = asset_returns - rf_daily
    aligned = pd.concat([excess.rename("asset"), factors], axis=1).dropna()

    if len(aligned) < max(30, len(factors.columns) + 5):
        return {}

    y = aligned["asset"].values
    X = np.column_stack([np.ones(len(aligned)),
                         aligned[list(factors.columns)].values])

    # OLS solution
    try:
        coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    except np.linalg.LinAlgError:
        return {}

    y_hat     = X @ coeffs
    residuals = y - y_hat
    n, k      = X.shape                       # k = 1 (intercept) + n_factors
    ss_res    = float(residuals @ residuals)
    ss_tot    = float(np.sum((y - y.mean()) ** 2))
    r2        = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    adj_r2    = 1.0 - (1 - r2) * (n - 1) / (n - k) if n > k else r2

    # Standard errors & t-stats
    sigma2   = ss_res / max(n - k, 1)
    try:
        cov_b = sigma2 * np.linalg.pinv(X.T @ X)
        se    = np.sqrt(np.maximum(np.diag(cov_b), 0.0))
    except Exception:
        se    = np.ones(k) * np.nan

    t_stats = coeffs / se

    factor_names = list(factors.columns)
    alpha_daily  = float(coeffs[0])

    return {
        "alpha_ann":    alpha_daily * 252,
        "alpha_daily":  alpha_daily,
        "betas":        {f: float(b) for f, b in zip(factor_names, coeffs[1:])},
        "t_alpha":      float(t_stats[0]),
        "t_stats":      {f: float(t) for f, t in zip(factor_names, t_stats[1:])},
        "r_squared":    r2,
        "adj_r2":       adj_r2,
        "idio_vol":     float(residuals.std()) * np.sqrt(252),
        "residuals":    pd.Series(residuals, index=aligned.index, name="residuals"),
    }


def rolling_beta(
    asset_returns: pd.Series,
    market_returns: pd.Series,
    rf_daily: float = 0.04 / 252,
    window: int = 63,
) -> pd.Series:
    """Rolling CAPM beta over a given window."""
    ea = asset_returns  - rf_daily
    em = market_returns - rf_daily

    def _beta(a, m):
        if m.var() < 1e-12:
            return np.nan
        return float(np.cov(a, m)[0, 1] / m.var())

    betas = [_beta(ea.iloc[i - window:i], em.iloc[i - window:i])
             for i in range(window, len(ea) + 1)]

    return pd.Series(betas, index=asset_returns.index[window - 1:])


def rolling_alpha(
    asset_returns: pd.Series,
    market_returns: pd.Series,
    rf_daily: float = 0.04 / 252,
    window: int = 63,
) -> pd.Series:
    """Rolling annualised Jensen's alpha."""
    ea = asset_returns  - rf_daily
    em = market_returns - rf_daily
    alphas = []

    for i in range(window, len(ea) + 1):
        a_w = ea.iloc[i - window:i].values
        m_w = em.iloc[i - window:i].values
        X   = np.column_stack([np.ones(window), m_w])
        try:
            c, *_ = np.linalg.lstsq(X, a_w, rcond=None)
            alphas.append(float(c[0]) * 252)
        except Exception:
            alphas.append(np.nan)

    return pd.Series(alphas, index=asset_returns.index[window - 1:])
