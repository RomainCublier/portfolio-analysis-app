"""Risk Lab: portfolio risk and performance analytics."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.data import download_adjusted_prices
from core.metrics import drawdown_curve, performance_metrics, portfolio_returns
from core.returns import compute_returns, cumulative_returns
from core.risk_contrib import volatility_contributions
from core.stress import default_stress_scenarios, evaluate_stress_scenarios
from core.var import historical_var, parametric_var


def _parse_manual_inputs(ticker_text: str, weight_text: str) -> pd.Series:
    tickers = [t.strip().upper() for t in ticker_text.split(",") if t.strip()]
    try:
        weight_values = [float(w.replace("%", "").strip()) for w in weight_text.split(",") if w.strip()]
    except ValueError as exc:  # noqa: BLE001
        raise ValueError("Weights could not be parsed; please use numbers separated by commas.") from exc

    if len(tickers) != len(weight_values):
        raise ValueError("The number of tickers and weights must match.")

    weights = pd.Series(weight_values, index=tickers, dtype=float)
    if weights.max() > 1.5:  # assume percentages
        weights = weights / 100

    total = weights.sum()
    if total <= 0:
        raise ValueError("Weights must be greater than zero.")

    return weights / total


def _get_date_range(lookback: str) -> tuple[datetime | None, datetime]:
    end = datetime.today()
    if lookback == "1y":
        start = end - timedelta(days=365)
    elif lookback == "3y":
        start = end - timedelta(days=365 * 3)
    elif lookback == "5y":
        start = end - timedelta(days=365 * 5)
    else:
        start = None
    return start, end


def _load_prices(tickers: List[str], start: datetime | None, end: datetime) -> pd.DataFrame:
    prices = download_adjusted_prices(tickers, start=start, end=end)
    available = [t for t in tickers if t in prices.columns]
    if not available:
        raise ValueError("None of the requested tickers returned price data.")
    return prices[available]


def _format_metric(value: float, pct: bool = True) -> str:
    if pct:
        return f"{value:.2%}"
    return f"{value:.2f}"


def _benchmark_returns(prices: pd.DataFrame, choice: str, frequency: str) -> pd.Series | None:
    if choice == "None":
        return None

    if choice == "SPY":
        tickers = ["SPY"]
        weights = pd.Series([1.0], index=tickers)
    else:  # 60/40
        tickers = ["SPY", "AGG"]
        weights = pd.Series([0.6, 0.4], index=tickers)

    if not set(tickers).issubset(prices.columns):
        return None

    bench_returns = compute_returns(prices[tickers], frequency)
    return portfolio_returns(bench_returns, weights)


def _portfolio_section_header():
    st.title("🧮 Risk Lab — Portfolio Analytics")
    st.caption("Assess risk, performance, and diversification without uploading CSV files.")


def main():
    _portfolio_section_header()

    with st.sidebar:
        st.header("Inputs")
        input_mode = st.radio("Portfolio source", ["Use generated portfolio (session)", "Manual input"])
        lookback = st.selectbox("Lookback", ["1y", "3y", "5y", "max"], index=0)
        frequency = st.selectbox("Frequency", ["daily", "weekly"], index=0)
        alpha = st.slider("VaR alpha", min_value=0.01, max_value=0.10, value=0.05, step=0.01)
        risk_free_rate = st.number_input("Risk-free rate (annual, decimal)", value=0.02, step=0.005, format="%.3f")
        benchmark = st.selectbox("Benchmark", ["None", "SPY", "60/40 (SPY+AGG)"])

        manual_tickers = "SPY, QQQ, AGG"
        manual_weights = "0.4, 0.3, 0.3"
        if input_mode == "Manual input":
            manual_tickers = st.text_input("Tickers (comma-separated)", manual_tickers)
            manual_weights = st.text_input("Weights (comma-separated)", manual_weights)

        run_analysis = st.button("Run Risk Lab")

    if not run_analysis:
        st.info("Configure the inputs in the sidebar and click **Run Risk Lab** to generate analytics.")
        st.stop()

    if input_mode == "Use generated portfolio (session)":
        session_weights = st.session_state.get("portfolio_weights")
        if session_weights is None or session_weights.empty:
            st.warning(
                "No generated portfolio found. Please create one in the Portfolio Generator first."
            )
            st.stop()
        weights = session_weights.astype(float)
    else:
        try:
            weights = _parse_manual_inputs(manual_tickers, manual_weights)
        except ValueError as exc:  # noqa: BLE001
            st.error(str(exc))
            st.stop()

    weights = weights.groupby(level=0).sum()
    weights = weights / weights.sum()

    start, end = _get_date_range(lookback)
    tickers = weights.index.tolist()

    benchmark_tickers: list[str] = []
    if benchmark == "SPY":
        benchmark_tickers = ["SPY"]
    elif benchmark.startswith("60/40"):
        benchmark_tickers = ["SPY", "AGG"]

    try:
        price_universe = _load_prices(list(dict.fromkeys(tickers + benchmark_tickers)), start, end)
    except Exception as exc:  # noqa: BLE001
        st.error(str(exc))
        st.stop()

    prices = price_universe[[t for t in tickers if t in price_universe.columns]]
    if prices.empty:
        st.error("Price data for the selected tickers is empty after cleaning.")
        st.stop()

    try:
        returns = compute_returns(prices, frequency)
    except Exception as exc:  # noqa: BLE001
        st.error(str(exc))
        st.stop()

    if returns.empty:
        st.error("No returns computed for the selected frequency.")
        st.stop()

    periods_per_year = 252 if frequency == "daily" else 52
    portfolio_ret = portfolio_returns(returns, weights)

    benchmark_ret = _benchmark_returns(price_universe, benchmark, frequency)

    metrics = performance_metrics(portfolio_ret, risk_free_rate=risk_free_rate, periods_per_year=periods_per_year)
    drawdown = drawdown_curve(portfolio_ret)

    hist_var, hist_cvar = historical_var(portfolio_ret, alpha)
    para_var, para_cvar = parametric_var(portfolio_ret, alpha)

    cov_matrix = returns.cov() * periods_per_year
    risk_contrib = volatility_contributions(weights, cov_matrix)

    correlation = returns.corr()

    stress_df = evaluate_stress_scenarios(weights, default_stress_scenarios(tickers))

    st.subheader("Portfolio Weights")
    # Build standardized weights_df for Plotly
    if isinstance(weights, pd.Series):
        weights_df = weights.rename("Weight").reset_index()
        weights_df.columns = ["Ticker", "Weight"]
    else:
        # fallback if weights already a df-like
        weights_df = pd.DataFrame(weights).copy()
        if "Ticker" not in weights_df.columns:
            weights_df = weights_df.reset_index().rename(columns={"index": "Ticker"})
        if "Weight" not in weights_df.columns and "weight" in weights_df.columns:
            weights_df = weights_df.rename(columns={"weight": "Weight"})

    weights_df["Ticker"] = weights_df["Ticker"].astype(str)
    weights_df["Weight"] = pd.to_numeric(weights_df["Weight"], errors="coerce")
    weights_df = weights_df.dropna(subset=["Ticker", "Weight"])

    if weights_df.empty or weights_df["Weight"].sum() == 0:
        st.warning("No valid weights to plot.")
    else:
        weights_df["Weight"] = weights_df["Weight"] / weights_df["Weight"].sum()
        pie_fig = px.pie(
            weights_df,
            names="Ticker",
            values="Weight",
            hole=0.3,
            title="Allocation"
        )
        st.plotly_chart(pie_fig, use_container_width=True)

    st.subheader("Performance")
    cum_portfolio = cumulative_returns(portfolio_ret)
    perf_fig = go.Figure()
    perf_fig.add_trace(
        go.Scatter(x=cum_portfolio.index, y=cum_portfolio.values, mode="lines", name="Portfolio")
    )
    if benchmark_ret is not None:
        cum_benchmark = cumulative_returns(benchmark_ret)
        perf_fig.add_trace(
            go.Scatter(x=cum_benchmark.index, y=cum_benchmark.values, mode="lines", name="Benchmark")
        )
    perf_fig.update_layout(template="plotly_white", yaxis_title="Growth of 1 unit")
    st.plotly_chart(perf_fig, use_container_width=True)

    draw_fig = go.Figure()
    draw_fig.add_trace(
        go.Scatter(
            x=drawdown.index,
            y=drawdown.values,
            fill="tozeroy",
            mode="lines",
            name="Drawdown",
            line_color="#EF553B",
        )
    )
    draw_fig.update_layout(template="plotly_white", yaxis_title="Drawdown", xaxis_title="Date")
    st.plotly_chart(draw_fig, use_container_width=True)

    st.subheader("Key Metrics")
    metrics_df = pd.DataFrame(
        {
            "Metric": ["CAGR", "Annual Volatility", "Sharpe", "Sortino", "Max Drawdown"],
            "Value": [
                _format_metric(metrics["CAGR"]),
                _format_metric(metrics["Annual Volatility"]),
                _format_metric(metrics["Sharpe"], pct=False),
                _format_metric(metrics["Sortino"], pct=False),
                _format_metric(metrics["Max Drawdown"]),
            ],
        }
    )
    st.dataframe(metrics_df, hide_index=True)

    st.subheader("Value-at-Risk")
    var_df = pd.DataFrame(
        {
            "Method": ["Historical", "Parametric (Normal)"],
            "VaR": [_format_metric(hist_var), _format_metric(para_var)],
            "CVaR": [_format_metric(hist_cvar), _format_metric(para_cvar)],
        }
    )
    st.dataframe(var_df, hide_index=True)

    st.subheader("Risk Contributions")
    contrib_df = risk_contrib.copy()
    contrib_df["Pct Contribution"] = contrib_df["Pct Contribution"].fillna(0)
    st.dataframe(contrib_df.style.format({"Contribution": "{:.4f}", "Pct Contribution": "{:.2%}"}))

    contrib_fig = px.bar(
        contrib_df.reset_index(),
        x="index",
        y="Pct Contribution",
        labels={"index": "Ticker", "Pct Contribution": "Risk Contribution"},
        title="Percentage of Portfolio Volatility",
    )
    st.plotly_chart(contrib_fig, use_container_width=True)

    st.subheader("Correlation Matrix")
    st.dataframe(correlation.style.format("{:.2f}"))

    st.subheader("Stress Scenarios")
    stress_df["Estimated Impact"] = stress_df["Estimated Impact"].apply(_format_metric)
    st.dataframe(stress_df, hide_index=True)


if __name__ == "__main__":
    main()
