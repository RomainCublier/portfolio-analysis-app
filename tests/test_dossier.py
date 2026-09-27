from datetime import date
import json
import pandas as pd
import pytest
from core.dossier import export_dossier, import_dossier, restore_dossier, COLUMNS
from core.planning import Project


def example():
    return {'project': Project(), 'allocation_draft': {'IE00B4K48X80': 1.0},
            'real_snapshot': (pd.DataFrame([['PEA', 'Test', 120.]], columns=COLUMNS), 30., date(2025, 1, 1)),
            'decision_journal': [{'date': '2025-01-01', 'note': 'Objectif inchangé.'}]}


def test_roundtrip_keeps_cash_date_positions_and_notes():
    state = {'real_positions_editor': {'edited_rows': {}}, 'allocation_old': 12}
    restore_dossier(state, import_dossier(export_dossier(example())))
    assert state['project'] == Project()
    assert state['real_snapshot'][1:] == (30., date(2025, 1, 1))
    assert state['real_positions'].iloc[0, 2] == 120
    assert state['decision_journal'][0]['note'] == 'Objectif inchangé.'
    assert 'real_positions_editor' not in state
    assert 'allocation_old' not in state
    assert json.loads(export_dossier(state)) == json.loads(export_dossier(example()))


@pytest.mark.parametrize('field,value', [('allocation', {'IE00B4K48X80': .9}), ('journal', [{'date': '2999-01-01', 'note': 'test'}]), ('snapshot', []), ('project', {'years': True})])
def test_invalid_import_does_not_mutate_existing_state(field, value):
    data = json.loads(export_dossier(example()))
    data[field] = value
    state = example()
    before = export_dossier(state)
    with pytest.raises(ValueError):
        restore_dossier(state, import_dossier(json.dumps(data)))
    assert export_dossier(state) == before


def test_duplicate_keys_and_nonfinite_values_rejected():
    with pytest.raises(ValueError):
        import_dossier('{"version":1,"version":1}')
    data = json.loads(export_dossier(example()))
    data['snapshot']['cash'] = float('nan')
    with pytest.raises(ValueError):
        import_dossier(json.dumps(data))


def test_empty_dossier_clears_previous_saved_state():
    state = example()
    restore_dossier(state, import_dossier(export_dossier({})))
    assert 'project' not in state and 'real_snapshot' not in state
    assert state['decision_journal'] == []
