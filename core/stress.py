"""Stress scenario helpers."""

from __future__ import annotations

from typing import Dict, Iterable

import pandas as pd


def default_stress_scenarios(tickers: Iterable[str]) -> Dict[str, Dict[str, float]]:
    """Return a set of simple stress scenarios keyed by name."""

    base_downside = {ticker: -0.15 for ticker in tickers}
    base_mild = {ticker: -0.05 for ticker in tickers}
    risk_on = {ticker: 0.08 for ticker in tickers}
    defensive = {ticker: 0.02 for ticker in tickers}

    return {
        "Equity sell-off (-15%)": base_downside,
        "Mild pullback (-5%)": base_mild,
        "Risk-on rally (+8%)": risk_on,
        "Defensive drift (+2%)": defensive,
    }


def evaluate_stress_scenarios(
    weights: pd.Series, scenarios: Dict[str, Dict[str, float]]
) -> pd.DataFrame:
    """Compute portfolio impact for each stress scenario."""

    results = []
    for name, shock_map in scenarios.items():
        aligned_shocks = pd.Series(shock_map).reindex(weights.index).fillna(0.0)
        scenario_return = float((aligned_shocks * weights).sum())
        results.append({"Scenario": name, "Estimated Impact": scenario_return})

    return pd.DataFrame(results)
