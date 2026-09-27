from datetime import date
from pathlib import Path

from streamlit.testing.v1 import AppTest

from core.dossier import export_dossier, import_dossier
from core.review import review_summary


def test_summary_uses_last_interval_and_separates_later_flows():
    values = [{'date': '2025-02-01', 'total': 1200}, {'date': '2025-01-01', 'total': 1000}]
    flows = [{'id': f'{index:032x}', 'date': when, 'amount': amount, 'note': ''}
             for index, (when, amount) in enumerate([
                 ('2025-01-01', 1000), ('2025-01-15', 300),
                 ('2025-02-01', -100), ('2025-02-02', 50)])]
    result = review_summary(values, flows, today=date(2025, 2, 3))
    assert result['latest']['total'] == 1200
    assert result['age_days'] == 2
    assert result['movement_count'] == 2
    assert result['declared_net_flows'] == 200
    assert result['pending_count'] == 1


def test_missing_history_is_not_reported_as_zero_performance():
    assert review_summary([], [])['latest'] is None
    result = review_summary([{'date': '2025-01-01', 'total': 0}], [])
    assert result['declared_net_flows'] is None
    assert result['previous'] is None


def test_review_empty_state_and_saved_note():
    root = Path(__file__).resolve().parents[1]
    app = AppTest.from_file(str(root / 'pages/revue.py')).run()
    assert not app.exception
    assert not app.text_area
    app.session_state['portfolio_valuations'] = [{'date': '2025-01-01', 'total': 1000}]
    app.run()
    assert not app.exception
    app.text_area[0].set_value('Mes chiffres sont à vérifier.')
    app.button[0].click().run()
    assert not app.exception
    journal = app.session_state['decision_journal']
    assert len(journal) == 1
    restored = import_dossier(export_dossier({'decision_journal': journal}))
    assert 'Mes chiffres sont à vérifier.' in restored['journal'][0]['note']
