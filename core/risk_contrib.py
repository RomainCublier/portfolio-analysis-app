"""Risk contribution calculations."""

from __future__ import annotations

import pandas as pd


def volatility_contributions(weights: pd.Series, cov_matrix: pd.DataFrame) -> pd.DataFrame:
    """Compute volatility contributions for each asset.

    Returns a dataframe with absolute and percentage contributions.
    """

    aligned_weights = weights.reindex(cov_matrix.index).fillna(0.0)
    portfolio_var = float(aligned_weights.T @ cov_matrix @ aligned_weights)

    if portfolio_var <= 0:
        contribution = pd.Series(0.0, index=cov_matrix.index)
    else:
        marginal_contrib = cov_matrix @ aligned_weights
        portfolio_vol = portfolio_var**0.5
        contribution = aligned_weights * marginal_contrib / portfolio_vol

    pct_contrib = contribution / contribution.sum() if contribution.sum() != 0 else contribution

    return pd.DataFrame(
        {
            "Contribution": contribution,
            "Pct Contribution": pct_contrib,
        }
    )
