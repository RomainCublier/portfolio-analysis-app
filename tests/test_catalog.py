from datetime import date
import json
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from core.catalog import load_catalog, review_status, valid_isin


def test_catalog_provenance_and_unknowns():
    rows = load_catalog()
    assert len(rows) == 10
    assert all(valid_isin(r["isin"]) for r in rows)
    assert sum(r["facts"]["fee_percent"] is not None for r in rows) == 8
    assert [r["isin"] for r in rows if r["facts"]["pea"] is True] == ["FR001400U5Q4"]
    assert all(r["market_data_status"] == "not_connected" for r in rows)
    assert all(r["commercial_rights"] != "approved" for r in rows)


def test_review_expiry_and_incomplete_are_not_verified():
    rows = load_catalog()
    assert review_status(rows[0], date(2026, 9, 21)) == "Caractéristiques documentées"
    assert review_status(next(r for r in rows if r["isin"] == "LU0290358497"), date(2026, 9, 21)) == "Fiche incomplète"
    assert review_status(rows[0], date(2027, 1, 1)) == "À revérifier"
    assert not valid_isin("IE00B4L5Y984")


def test_duplicate_isins_rejected(tmp_path):
    rows = load_catalog()
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps({"schema_version": 2, "instruments": [rows[0], rows[0]]}))
    with pytest.raises(ValueError):
        load_catalog(path)


def test_catalog_ui_filters_and_handles_no_results():
    root = Path(__file__).resolve().parents[1]
    app = AppTest.from_file(str(root / "pages/catalogue.py")).run()
    assert not app.exception
    assert len(app.expander) == 10
    app.checkbox[0].check().run()
    assert not app.exception
    assert len(app.expander) == 1
    assert "Amundi PEA Monde" in app.expander[0].label
    app.text_input[0].set_value("introuvable").run()
    assert not app.exception
    assert len(app.expander) == 0
