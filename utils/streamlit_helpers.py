"""Streamlit helper utilities for allocations and error handling."""

from typing import Iterable


def allocation_percent_to_weights(df, allocation_column="Allocation (%)", weight_column="Poids"):
    """Return a copy of *df* with decimal weights computed from percentage allocations.

    The function is tolerant to missing columns and will raise a descriptive error if
    the allocation column cannot be found.
    """

    if allocation_column not in df.columns:
        raise KeyError(f"Column '{allocation_column}' not found in dataframe")

    df_copy = df.copy()
    df_copy[weight_column] = df_copy[allocation_column].astype(float) / 100
    return df_copy


def handle_network_error(exc: Exception) -> str:
    """Produce a user-friendly message for network-related exceptions."""

    network_errors: Iterable[str] = (
        "ConnectionError",
        "Timeout",
        "HTTPError",
        "URLError",
        "SSLError",
        "ProxyError",
    )

    exc_name = exc.__class__.__name__
    message = str(exc)
    lowered_message = message.lower()

    if any(keyword in exc_name for keyword in network_errors):
        return (
            "Network issue detected while retrieving data. Please check your "
            "connection or try again in a few minutes."
        )

    if any(
        marker in lowered_message
        for marker in ("proxyerror", "connect tunnel failed", "failed downloads", "timeout")
    ):
        return (
            "Market data download failed due to a network/proxy issue. "
            "Please verify internet access to Yahoo Finance and try again."
        )

    return message
