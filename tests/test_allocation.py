from datetime import date
from pathlib import Path
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from core.allocation import HoldingsSnapshot, allocation_diagnostics, covariance_risk

TODAY = date(2026, 9, 21)


def snapshot(holdings, as_of=TODAY):
    return HoldingsSnapshot(as_of, "https://example.org/artificial-test-composition", holdings)


def test_overlap_adds_direct_and_fund_exposure_without_renormalization():
    report = allocation_diagnostics({"stock": .2, "fund": .8}, {"stock": "Action", "fund": "Fonds"},
        {"stock": snapshot({"issuer": 1.}), "fund": snapshot({"issuer": .1})}, TODAY, {"issuer": .25})
    assert report["known_issuers"]["issuer"] == pytest.approx(.28)
    assert report["unknown_weight"] == pytest.approx(.72)
    assert report["checks"][0]["status"] == "Dépassée"


def test_unknown_holdings_never_pass_issuer_limit():
    report = allocation_diagnostics({"fund": 1.}, {"fund": "ETF"}, {}, TODAY, {"issuer": .1})
    assert report["checks"][0]["status"] == "Indéterminée"
    assert report["unknown_weight"] == 1


def test_complete_coverage_and_stock_picking_are_separate():
    report = allocation_diagnostics({"fund": .8, "stock": .2}, {"fund": "Fonds", "stock": "Action"},
        {"fund": snapshot({"A": .5, "B": .5}), "stock": snapshot({"A": 1.})}, TODAY,
        {"stock_picking": .1, "issuer": .7})
    assert report["unknown_weight"] == 0
    assert report["direct_stock_weight"] == .2
    assert [x["status"] for x in report["checks"]] == ["Dépassée", "Respectée sur ce critère"]


@pytest.mark.parametrize("as_of", [date(2025, 1, 1), date(2027, 1, 1)])
def test_stale_or_future_compositions_are_excluded(as_of):
    report = allocation_diagnostics({"F": 1.}, {"F": "Fonds"}, {"F": snapshot({"A": 1.}, as_of)}, TODAY)
    assert report["unknown_weight"] == 1
    assert report["stale_snapshots"] == ["F"]


@pytest.mark.parametrize("holdings", [{"A": -.1}, {"A": float("nan")}, {"A": .8, "B": .8}])
def test_invalid_or_leveraged_holdings_rejected(holdings):
    with pytest.raises(ValueError):
        allocation_diagnostics({"F": 1.}, {"F": "Fonds"}, {"F": snapshot(holdings)}, TODAY)


def test_covariance_risk_matches_hand_calculation_and_euler_sum():
    cov = pd.DataFrame([[.04, 0], [0, .01]], index=["A", "B"], columns=["A", "B"])
    r = covariance_risk({"A": .5, "B": .5}, cov)
    assert r["variance"] == pytest.approx(.0125)
    assert r["volatility"] == pytest.approx(.0125 ** .5)
    assert sum(r["volatility_contributions"].values()) == pytest.approx(r["volatility"])
    assert covariance_risk({"B": .5, "A": .5}, cov)["variance"] == pytest.approx(.0125)


def test_negative_risk_contribution_is_preserved():
    cov = pd.DataFrame([[.04, -.01], [-.01, .01]], index=["A", "B"], columns=["A", "B"])
    r = covariance_risk({"A": .9, "B": .1}, cov)
    assert r["volatility_contributions"]["B"] < 0
    assert sum(r["volatility_contributions"].values()) == pytest.approx(r["volatility"])


def test_invalid_covariance_and_weights_are_rejected():
    cov = pd.DataFrame([[1, 2], [2, 1]], index=["A", "B"], columns=["A", "B"])
    with pytest.raises(ValueError, match="positive"):
        covariance_risk({"A": .5, "B": .5}, cov)
    with pytest.raises(ValueError, match="100"):
        allocation_diagnostics({"A": .3}, {"A": "Action"}, {}, TODAY)


def test_allocation_ui_requires_full_weights_and_warns_on_unknown_exposures():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "pages/allocation.py")).run()
    assert not app.exception
    assert len(app.multiselect[0].options) == 10
    app.multiselect[0].set_value(["FR0000121014", "FR0000284689"]).run()
    app.button[0].click().run()
    assert "100" in app.error[0].value
    app.number_input[0].set_value(20)
    app.number_input[1].set_value(80)
    app.checkbox[2].check().run()
    app.button[0].click().run()
    assert not app.exception
    assert not app.error
    assert app.warning
    assert app.dataframe[-1].value.iloc[0]["Résultat"] == "Indéterminée"
