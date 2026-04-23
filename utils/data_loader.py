"""Data loading utilities (e.g., Yahoo Finance downloads with sane defaults)."""

from functools import lru_cache
from typing import Dict, Iterable, List, Optional

import pandas as pd
import yfinance as yf

from config.assumptions import DEFAULT_END_DATE, DEFAULT_START_DATE
from utils.streamlit_helpers import handle_network_error


@lru_cache(maxsize=16)
def _download_price_data_cached(
    tickers_key: tuple,
    start: Optional[str] = DEFAULT_START_DATE,
    end: Optional[str] = DEFAULT_END_DATE,
    period: Optional[str] = None,
) -> pd.DataFrame:
    tickers_list = list(tickers_key)

    try:
        data = yf.download(
            tickers_list,
            start=None if period else start,
            end=None if period else end,
            period=period,
            progress=False,
        )
    except Exception as exc:  # noqa: BLE001 - handled explicitly below
        raise ValueError(handle_network_error(exc)) from exc

    if data.empty:
        raise ValueError(
            "No market data retrieved for the provided tickers. "
            "This is often caused by a temporary Yahoo Finance/network restriction."
        )

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

    if len(tickers_list) == 1:
        data.columns = [tickers_list[0]]

    return data.dropna(axis=1, how="all")


def download_price_data(
    tickers: Iterable[str],
    start: Optional[str] = DEFAULT_START_DATE,
    end: Optional[str] = DEFAULT_END_DATE,
    period: Optional[str] = None,
) -> pd.DataFrame:
    """Download adjusted close prices for a list of tickers.

    Raises a ValueError with a user-friendly message if no data is returned or a
    network issue is detected.
    """

    tickers_key = tuple(tickers)
    return _download_price_data_cached(tickers_key, start=start, end=end, period=period)


def ensure_valid_tickers(data: pd.DataFrame, tickers: List[str]) -> List[str]:
    """Return the subset of tickers available in the downloaded dataframe."""

    valid = [t for t in tickers if t in data.columns]
    if not valid:
        raise ValueError(f"No valid tickers found among: {tickers}")
    return valid


def fetch_asset_profile(ticker: str) -> Dict[str, Optional[str]]:
    """Retrieve descriptive information for a given ticker via yfinance."""

    try:
        info = yf.Ticker(ticker).get_info()
    except Exception as exc:  # noqa: BLE001 - handled explicitly below
        raise ValueError(handle_network_error(exc)) from exc

    if not info:
        raise ValueError("No descriptive information available for this asset.")

    return {
        "name": info.get("longName") or info.get("shortName") or ticker,
        "instrument_type": info.get("quoteType") or info.get("typeDisp"),
        "exchange": info.get("exchange") or info.get("fullExchangeName"),
        "currency": info.get("currency") or info.get("financialCurrency"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "country": info.get("country"),
        "fullTimeEmployees": info.get("fullTimeEmployees"),
        "marketCap": info.get("marketCap"),
        "website": info.get("website"),
        "first_trade_date": info.get("firstTradeDateEpochUtc") or info.get("firstTradeDateEpoch"),
        "summary": info.get("longBusinessSummary") or info.get("description"),
    }
