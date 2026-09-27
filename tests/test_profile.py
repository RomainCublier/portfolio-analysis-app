from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core.catalog import load_catalog
from core.planning import Project
from core.profile import matching_catalog_rows, profile_frame

ROOT = Path(__file__).resolve().parents[1]


def test_beginner_short_horizon_is_defensive_and_diversified_first():
    frame = profile_frame(Project(years=2, loss_reaction="J’aurais besoin de récupérer cet argent"))
    assert frame.horizon_bucket == "Court terme"
    assert frame.risk_budget == "Préservation prioritaire"
    assert frame.equity_ceiling == pytest.approx(0.35)
    assert frame.stock_picking_cap == 0
    assert any(block["role"] == "Liquidités / monétaire" for block in frame.building_blocks)
    assert not any(block["role"] == "Actions individuelles" for block in frame.building_blocks)


def test_experienced_long_horizon_allows_satellite_stock_picking_not_core():
    frame = profile_frame(Project(years=20, experience="J’ai déjà investi",
                                  loss_reaction="Je pourrais attendre malgré la baisse"))
    assert frame.risk_budget == "Croissance assumée"
    assert frame.equity_floor == pytest.approx(0.60)
    assert frame.stock_picking_cap == pytest.approx(0.20)
    assert any(block["role"] == "Fonds actifs" for block in frame.building_blocks)
    stock_blocks = [block for block in frame.building_blocks if block["role"] == "Actions individuelles"]
    assert len(stock_blocks) == 1
    assert "Satellite" in stock_blocks[0]["use"]


def test_matching_catalog_rows_uses_documented_catalog_only():
    rows = load_catalog()
    block = {"catalog_filter": "marchés développés"}
    matches = matching_catalog_rows(rows, block)
    assert matches
    assert all("source_url" in row and row["source_url"].startswith("https://") for row in matches)


def test_profile_page_runs_from_default_project():
    app = AppTest.from_file(str(ROOT / "pages/profil.py")).run()
    assert not app.exception
    assert app.title[0].value == "Comprendre mon profil"
    assert app.metric[0].label == "Horizon"
    assert any("Fourchette pédagogique" in item.value for item in app.markdown)
