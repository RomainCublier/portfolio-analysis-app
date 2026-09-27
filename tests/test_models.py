from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core.catalog import load_catalog
from core.dossier import export_dossier, import_dossier
from core.models import MODELS, model_weights, hypothetical_change, keep_model
from core.planning import Project
from core.models import saved_choices


def test_resume_exact_model_without_coercing_custom_portfolio():
    assert saved_choices({'IE00B4L5Y983': .6, 'IE00BDBRDM35': .4}) == ('60/40', 'IE00B4L5Y983', 'IE00BDBRDM35')
    assert saved_choices({'IE00B4L5Y983': .61, 'IE00BDBRDM35': .39}) == (None, None, None)
    assert saved_choices({}) == (None, None, None)


@pytest.mark.parametrize('model', MODELS)
def test_complete_allocations_and_dossier_roundtrip(model):
    weights = model_weights(model, 'FR0000284689', 'IE00BDBRDM35', load_catalog())
    assert sum(weights.values()) == pytest.approx(1)
    state = {'allocation_FR0000284689': 5, 'project': Project(), 'decision_journal': []}
    keep_model(state, weights)
    assert 'allocation_FR0000284689' not in state
    assert state['project'] == Project()
    assert import_dossier(export_dossier(state))['allocation'] == weights


def test_no_unknown_instruments_or_fabricated_catalog_rows():
    with pytest.raises(ValueError):
        model_weights('60/40', 'FR0000121014', 'IE00BDBRDM35', load_catalog())
    with pytest.raises(ValueError):
        model_weights('60/40', 'FR0000284689', 'IE00BDBRDM35', [])
    assert hypothetical_change('60/40', -.30, -.10) == pytest.approx(-.22)
    assert hypothetical_change('90/10', -1, -1) == -1
    with pytest.raises(ValueError):
        hypothetical_change('60/40', float('nan'), 0)


def test_guided_flow_requires_choices_and_saves_to_existing_dossier():
    root = Path(__file__).resolve().parents[1]
    app = AppTest.from_file(str(root / 'pages/modeles.py')).run()
    assert not app.exception
    assert not app.radio
    app.session_state['project'] = Project(initial=1000)
    app.run()
    assert app.radio[0].value is None
    app.radio[0].set_value('60/40').run()
    assert not app.exception
    assert next(b for b in app.button if b.label == 'Garder ce portefeuille fictif').disabled
    app.selectbox[0].select('IE00B4L5Y983')
    app.selectbox[1].select('IE00BDBRDM35').run()
    save = next(b for b in app.button if b.label == 'Garder ce portefeuille fictif')
    assert not save.disabled
    save.click().run()
    assert not app.exception
    assert app.session_state['allocation_draft'] == {'IE00B4L5Y983': .6, 'IE00BDBRDM35': .4}
