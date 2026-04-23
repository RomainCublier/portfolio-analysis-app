"""ETF & fund due diligence utilities."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Tuple

import numpy as np
import pandas as pd


def get_etf_identity(ticker: str) -> Dict[str, str]:
    """Return basic identity attributes for an ETF.

    Values are mocked when metadata is unavailable so the UI can render
    without external lookups. The function can be extended to use full
    fund databases when available.
    """

    sample_profiles = {
        "SPY": {
            "asset_class": "Equity",
            "currency": "USD",
            "replication": "Physical",
            "ter": "0.09%",
            "domicile": "US",
        },
        "AGG": {
            "asset_class": "Fixed Income",
            "currency": "USD",
            "replication": "Physical",
            "ter": "0.03%",
            "domicile": "US",
        },
        "EFA": {
            "asset_class": "Equity",
            "currency": "USD",
            "replication": "Optimised sampling",
            "ter": "0.33%",
            "domicile": "US",
        },
    }

    ticker_upper = ticker.upper()
    default_profile = {
        "asset_class": "Multi-asset",
        "currency": "USD",
        "replication": "Physical",
        "ter": "N/A",
        "domicile": "Unknown",
    }
    profile = sample_profiles.get(ticker_upper, default_profile)
    profile["ticker"] = ticker_upper
    return profile


def _annualization_factor(index: pd.Index) -> float:
    if isinstance(index, pd.DatetimeIndex) and len(index) > 1:
        median_spacing = index.to_series().diff().dt.days.dropna().median()
        if median_spacing and median_spacing > 4:
            return 52
    return 252


def compute_tracking_metrics(
    etf_returns: pd.Series, benchmark_returns: pd.Series
) -> Dict[str, float]:
    """Calculate tracking difference and tracking error versus a benchmark."""

    aligned = pd.concat([etf_returns, benchmark_returns], axis=1, join="inner").dropna()
    if aligned.empty:
        return {"tracking_difference": np.nan, "tracking_error": np.nan}

    diff = aligned.iloc[:, 0] - aligned.iloc[:, 1]
    factor = _annualization_factor(aligned.index)
    tracking_difference = diff.mean() * factor
    tracking_error = diff.std() * np.sqrt(factor)

    return {
        "tracking_difference": float(tracking_difference),
        "tracking_error": float(tracking_error),
    }


def liquidity_proxies(price_df: pd.DataFrame) -> Dict[str, float]:
    """Estimate liquidity using basic proxies such as volume and return behaviour."""

    if price_df is None or price_df.empty:
        return {"average_volume": np.nan, "volatility_proxy": np.nan, "zero_return_pct": np.nan}

    result: Dict[str, float] = {"average_volume": np.nan, "volatility_proxy": np.nan, "zero_return_pct": np.nan}

    volume_cols = [col for col in price_df.columns if str(col).lower().endswith("volume") or str(col).lower() == "volume"]
    price_cols = [col for col in price_df.columns if col not in volume_cols]

    price_series = price_df[price_cols[0]] if price_cols else price_df.iloc[:, 0]
    returns = price_series.pct_change().dropna()
    if not returns.empty:
        result["volatility_proxy"] = float(returns.std() * np.sqrt(_annualization_factor(price_df.index)))
        zero_mask = returns.abs() < 1e-9
        result["zero_return_pct"] = float(zero_mask.mean()) if len(returns) > 0 else np.nan

    if volume_cols:
        result["average_volume"] = float(price_df[volume_cols[0]].dropna().mean())

    return result


def stress_metrics(
    returns: pd.Series, stress_periods: Dict[str, Tuple[datetime, datetime]]
) -> pd.DataFrame:
    """Assess ETF behaviour during named stress windows."""

    if returns is None or returns.empty or not stress_periods:
        return pd.DataFrame(columns=["Scenario", "Drawdown", "Recovery Days"])

    growth = (1 + returns).cumprod()
    metrics: list[Dict[str, float | str]] = []

    for name, (start, end) in stress_periods.items():
        period_returns = returns.loc[start:end]
        if period_returns.empty:
            continue

        pre_window = growth.loc[: start]
        start_value = pre_window.iloc[-1] if not pre_window.empty else growth.iloc[0]

        segment_growth = growth.loc[start:end] / start_value
        drawdown_series = (segment_growth / segment_growth.cummax()) - 1
        period_drawdown = float(drawdown_series.min()) if not drawdown_series.empty else np.nan

        post_period = growth.loc[end:]
        recovery_days = np.nan
        if not post_period.empty:
            recovered = post_period[post_period >= start_value]
            if not recovered.empty:
                recovery_days = float((recovered.index[0] - period_returns.index[-1]).days)

        metrics.append({"Scenario": name, "Drawdown": period_drawdown, "Recovery Days": recovery_days})

    return pd.DataFrame(metrics)


def portfolio_fit_summary(metrics_dict: Dict[str, float]) -> str:
    """Provide a qualitative summary of the ETF's portfolio role."""

    te = metrics_dict.get("tracking_error")
    vol = metrics_dict.get("volatility")
    dd = metrics_dict.get("max_drawdown")
    liquidity = metrics_dict.get("average_volume")

    if te is not None and not np.isnan(te) and te < 0.03:
        if vol is not None and not np.isnan(vol) and vol < 0.15:
            return "core allocation"
        return "beta exposure with tight tracking"

    if dd is not None and not np.isnan(dd) and dd > -0.10:
        return "defensive diversifier"

    if liquidity is not None and not np.isnan(liquidity) and liquidity < 100000:
        return "niche sleeve with limited liquidity"

    if vol is not None and not np.isnan(vol) and vol > 0.25:
        return "risk amplifier"

    return "satellite position"
