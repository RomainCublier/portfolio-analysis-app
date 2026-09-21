from dataclasses import replace
import numpy as np
import pandas as pd
import pytest
from core.history import SeriesMetadata, buy_and_hold, path_metrics, periodic_sharpe, validate_panel


@pytest.fixture
def sample():
    dates = pd.date_range("2025-01-01", periods=3)
    levels = pd.DataFrame({"A": [100., 80., 100.], "B": [100., 100., 100.]}, index=dates)
    metadata = {key: SeriesMetadata(key, "EUR", "https://example.org/synthetic-fixture",
        "2025-01-04T00:00:00Z", "2025-01-01", "net_total_return", "synthetic", "unknown", "", "0" * 64) for key in levels}
    return dates, levels, metadata


def test_initial_loss_is_included_and_buy_hold_weights_drift(sample):
    dates, levels, meta = sample
    curve, report = buy_and_hold(levels, {"A": .5, "B": .5}, meta, dates)
    assert curve.tolist() == pytest.approx([1, .9, 1])
    assert path_metrics(curve)["max_drawdown"] == pytest.approx(-.1)
    # Daily rebalancing would return 1.0125; buy-and-hold returns 1.
    assert path_metrics(curve)["total_return"] == 0
    assert report["origins"] == {"A": "synthetic", "B": "synthetic"}
    assert len(report["normalized_sha256"]) == 64


@pytest.mark.parametrize("value", [np.nan, np.inf, 0, -1])
def test_invalid_prices_are_not_silently_filled(sample, value):
    dates, levels, meta = sample
    levels.loc[dates[1], "A"] = value
    with pytest.raises(ValueError):
        buy_and_hold(levels, {"A": .5, "B": .5}, meta, dates)


def test_missing_observation_and_duplicate_dates_block(sample):
    dates, levels, meta = sample
    with pytest.raises(ValueError, match="calendrier"):
        validate_panel(levels.drop(dates[1]), meta, dates)
    levels.index = pd.DatetimeIndex([dates[0], dates[0], dates[2]])
    with pytest.raises(ValueError, match="uniques"):
        validate_panel(levels, meta, dates)


@pytest.mark.parametrize("changes", [
    {"currency": "USD"}, {"return_basis": "raw_close"}, {"inception_date": "2025-01-02"},
    {"raw_sha256": ""}, {"instrument_id": "wrong"}, {"retrieved_at": "2024-12-31"},
])
def test_metadata_incompatibilities_block(sample, changes):
    dates, levels, meta = sample
    meta["A"] = replace(meta["A"], **changes)
    with pytest.raises(ValueError):
        validate_panel(levels, meta, dates)


def test_unknown_rights_and_synthetic_origin_block_commercial(sample):
    dates, levels, meta = sample
    with pytest.raises(ValueError, match="droits"):
        validate_panel(levels, meta, dates, commercial=True)
    approved = {key: replace(m, origin="fund", license_status="approved", license_reference="test-license") for key, m in meta.items()}
    validate_panel(levels, approved, dates, commercial=True)
    approved["A"] = replace(approved["A"], origin="proxy")
    with pytest.raises(ValueError):
        validate_panel(levels, approved, dates, commercial=True)


@pytest.mark.parametrize("weights", [{"A": 1}, {"A": .5, "B": .6}, {"A": -.5, "B": 1.5}, {"A": np.nan, "B": 1}, {"A": True, "B": 0}])
def test_invalid_weights_block(sample, weights):
    dates, levels, meta = sample
    with pytest.raises(ValueError):
        buy_and_hold(levels, weights, meta, dates)


def test_calendar_cagr_and_no_double_fee():
    curve = pd.Series([100., 110.], index=pd.to_datetime(["2024-01-01", "2025-01-01"]))
    assert path_metrics(curve)["cagr"] == pytest.approx(1.1 ** (365.25 / 366) - 1)


def test_sharpe_uses_periodic_arithmetic_excess_returns():
    returns = pd.Series([.01, .03, -.01])
    rf = pd.Series([.001, .001, .001])
    assert periodic_sharpe(returns, rf) == pytest.approx(.009 / .02)
    assert periodic_sharpe(pd.Series([0., 0.]), pd.Series([0., 0.])) is None
    with pytest.raises(ValueError):
        periodic_sharpe(returns, rf.iloc[::-1])
