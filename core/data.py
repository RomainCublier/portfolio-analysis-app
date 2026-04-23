"""Data utilities for Risk Lab analytics."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional

import pandas as pd
import yfinance as yf

from utils.streamlit_helpers import handle_network_error


def _extract_adjusted_close(data: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    """Return adjusted close prices from a yfinance download result.

    The helper normalizes single- and multi-ticker downloads to a simple dataframe
    indexed by date with ticker symbols as columns.
    """

    if data.empty:
        raise ValueError("No market data retrieved for the provided tickers.")

    if isinstance(data.columns, pd.MultiIndex):
        if "Adj Close" in data.columns.levels[0]:
            data = data["Adj Close"]
        else:
            first_layer = data.columns.levels[0][0]
            data = data[first_layer]
    elif "Adj Close" in data.columns:
        data = pd.DataFrame(data["Adj Close"])
    elif "Close" in data.columns:
        data = pd.DataFrame(data["Close"])
    else:
        data = pd.DataFrame(data.iloc[:, -1])

    if len(tickers) == 1:
        data.columns = [tickers[0]]

    return data


def download_adjusted_prices(
    tickers: Iterable[str],
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> pd.DataFrame:
    """Download adjusted prices for the provided tickers using yfinance.

    Prices are forward-filled, and rows with all missing values are dropped.
    """

    clean_tickers = [t.strip().upper() for t in tickers if t and str(t).strip()]
    if not clean_tickers:
        raise ValueError("Please provide at least one valid ticker symbol.")

    try:
        data = yf.download(clean_tickers, start=start, end=end, progress=False)
    except Exception as exc:  # noqa: BLE001 - handled for user-facing display
        raise ValueError(handle_network_error(exc)) from exc
    prices = _extract_adjusted_close(data, clean_tickers)
    prices = prices.ffill().dropna(how="all")

    if prices.empty:
        raise ValueError(
            "Price series is empty after cleaning. Check tickers/dates or "
            "internet access to Yahoo Finance."
        )

    return prices
