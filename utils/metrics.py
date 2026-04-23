"""Portfolio and asset metric calculations."""

import pandas as pd


def compute_portfolio_metrics(portfolio_values: pd.Series) -> dict:
    """Return key performance metrics for a portfolio value series."""

    returns = portfolio_values.pct_change().dropna()
    cumulative_return = (portfolio_values.iloc[-1] / portfolio_values.iloc[0]) - 1
    annualized_return = (1 + cumulative_return) ** (252 / len(portfolio_values)) - 1
    volatility = returns.std() * (252 ** 0.5)
    sharpe = annualized_return / volatility if volatility != 0 else 0

    return {
        "Cumulative Return": f"{cumulative_return:.2%}",
        "Annualized Return": f"{annualized_return:.2%}",
        "Volatility (ann.)": f"{volatility:.2%}",
        "Sharpe Ratio": f"{sharpe:.2f}",
    }


def compute_asset_metrics(adjusted_close: pd.Series) -> dict:
    """Compute advanced diagnostics for a single asset."""

    df = adjusted_close.to_frame("Adj Close")
    df["Daily Return"] = df["Adj Close"].pct_change()
    df = df.dropna()

    start_price = df["Adj Close"].iloc[0]
    end_price = df["Adj Close"].iloc[-1]
    years = max(len(df) / 252, 1e-6)
    cagr = (end_price / start_price) ** (1 / years) - 1

    vol = df["Daily Return"].std() * (252 ** 0.5)
    sharpe = cagr / vol if vol != 0 else 0

    cumulative = (1 + df["Daily Return"]).cumprod()
    running_max = cumulative.cummax()
    drawdowns = (cumulative / running_max) - 1
    max_drawdown = drawdowns.min()

    best_day = df["Daily Return"].max()
    worst_day = df["Daily Return"].min()

    return {
        "CAGR": cagr,
        "Volatility (ann.)": vol,
        "Sharpe Ratio": sharpe,
        "Max Drawdown": max_drawdown,
        "Best Day": best_day,
        "Worst Day": worst_day,
    }
