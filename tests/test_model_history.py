from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from core.catalog import load_catalog
from core.history import SeriesMetadata
from core.model_history import coverage, compare_models
from core.planning import Project

STOCK, BOND = 'IE00B4L5Y983', 'IE00BDBRDM35'


def fixture():
    # Fabricated test observations; never shipped as market data.
    dates = pd.to_datetime(['2024-12-31', '2025-01-31', '2025-02-28'])
    levels = pd.DataFrame({STOCK: [100., 100., 100.], BOND: [100., 100., 100.]}, index=dates)
    metadata = {key: SeriesMetadata(key, 'EUR', 'https://example.org/test-only',
        '2025-03-01', '2020-01-01', 'net_total_return', 'fund', 'unknown', '', 'a' * 64) for key in levels}
    return levels, metadata, dates, {}


def test_all_three_models_reuse_project_contributions_without_inventing_returns():
    table, curves, flows = compare_models(fixture(), STOCK, BOND, load_catalog(), Project(initial=1000, monthly=100))
    assert table['Total versé (€)'].tolist() == [1200] * 3
    assert table['Valeur finale (€)'].tolist() == pytest.approx([1200] * 3)
    assert table['Performance hors effet des apports (%)'].tolist() == pytest.approx([0] * 3)
    assert list(curves) == ['30/70', '60/40', '90/10']
    assert flows.tolist() == [0, 100, 100]


def test_missing_or_proxy_data_is_not_substituted():
    assert coverage({STOCK: .6, BOND: .4}, None)[0] == sorted([STOCK, BOND])
    data = fixture()
    assert coverage({'missing': 1}, data)[0] == ['missing']
    with pytest.raises(ValueError, match='manquant'):
        compare_models(data, 'missing', BOND, load_catalog(), Project(initial=1000))
    data[1][STOCK] = replace(data[1][STOCK], origin='proxy')
    with pytest.raises(ValueError, match='proxy'):
        compare_models(data, STOCK, BOND, load_catalog(), Project(initial=1000))


def test_calendar_gap_and_zero_initial_capital_rejected():
    data = fixture()
    with pytest.raises(ValueError, match='incomplet'):
        compare_models((data[0].iloc[[0, 2]], *data[1:]), STOCK, BOND, load_catalog(), Project(initial=1000))
    with pytest.raises(ValueError, match='positif'):
        compare_models(data, STOCK, BOND, load_catalog(), Project())


def test_central_page_displays_comparison_without_manual_weight_reentry():
    root = Path(__file__).resolve().parents[1]
    app = AppTest.from_file(str(root / 'pages/modeles.py'))
    app.session_state['project'] = Project(initial=1000, monthly=100)
    app.session_state['research_history'] = fixture()
    app.run().radio[0].set_value('60/40').run()
    app.selectbox[0].select(STOCK)
    app.selectbox[1].select(BOND).run()
    next(b for b in app.button if b.label == 'Comparer les trois répartitions sur cet historique').click().run()
    assert not app.exception
    assert any('Valeur finale (€)' in d.value.columns for d in app.dataframe)
    app.run()
    assert not app.exception
    assert any('Valeur finale (€)' in d.value.columns for d in app.dataframe)
    app.session_state['project'] = Project(initial=2000, monthly=100)
    app.run()
    assert not app.exception
    assert not any('Valeur finale (€)' in d.value.columns for d in app.dataframe)
    assert any('Relancez la comparaison' in info.value for info in app.info)
