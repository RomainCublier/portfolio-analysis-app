from datetime import date
import json
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from pathlib import Path
from core.tracking import period_result, upsert_valuation, validate_tracking
from core.dossier import export_dossier, import_dossier, restore_dossier, COLUMNS

ROOT = Path(__file__).resolve().parents[1]


def valuation(when, total):
    return {'date': when, 'total': total}


def flow(when, amount, identifier='a' * 32):
    return {'date': when, 'amount': amount, 'id': identifier, 'note': ''}


def test_cfa_handbook_example_with_signed_daily_weights():
    # Official handbook section 2: 31 May -> 30 June, outflow June 6,
    # inflow June 11; 30 calendar days, end-of-day convention.
    result = period_result(valuation('2025-05-31', 100_000), valuation('2025-06-30', 135_000),
        [flow('2025-06-06', -2000), flow('2025-06-11', 20_000, 'b' * 32)], complete=True)
    assert result['net_external_flows'] == 18_000
    assert result['gain_loss_eur'] == 17_000
    assert [f['weight'] for f in result['flows']] == pytest.approx([.8, 19 / 30])
    assert result['estimated_return'] == pytest.approx(17_000 / 111_066.66666666667)


def test_cash_only_deposit_is_not_a_profit():
    result = period_result(valuation('2025-01-01', 1000), valuation('2025-01-11', 1500),
                          [flow('2025-01-06', 500)], complete=True)
    assert result['weighted_capital'] == 1250
    assert result['estimated_return'] == 0
    assert result['gain_loss_eur'] == 0


def test_start_flows_excluded_end_flows_have_zero_weight():
    result = period_result(valuation('2025-01-01', 1000), valuation('2025-01-11', 900),
        [flow('2025-01-01', 1000), flow('2025-01-11', -200, 'b' * 32)], complete=True)
    assert result['net_external_flows'] == -200
    assert result['gain_loss_eur'] == 100
    assert result['estimated_return'] == .1
    assert result['flows'][0]['weight'] == 0


def test_distinct_same_day_deposits_both_counted():
    result = period_result(valuation('2025-01-01', 1000), valuation('2025-01-11', 1400),
        [flow('2025-01-06', 200), flow('2025-01-06', 200, 'b' * 32)], complete=True)
    assert result['net_external_flows'] == 400
    assert result['estimated_return'] == 0


@pytest.mark.parametrize('complete', [False, None, 1, 'yes'])
def test_no_result_without_explicit_completeness(complete):
    with pytest.raises(ValueError):
        period_result(valuation('2025-01-01', 100), valuation('2025-02-01', 110), [], complete=complete)


@pytest.mark.parametrize('start,end,flows', [
    (0, 100, [flow('2025-01-06', 100)]),
    (100, 0, [flow('2025-01-02', -200)]),
    (100, 0, [flow('2025-01-06', 1000)]),
])
def test_uninterpretable_percentage_is_withheld(start, end, flows):
    report = period_result(valuation('2025-01-01', start), valuation('2025-01-11', end), flows, complete=True)
    assert report['estimated_return'] is None
    assert report['unavailable_reason']


@pytest.mark.parametrize('rows,flows', [
    ([valuation('2999-01-01', 10)], []),
    ([valuation('2025-01-01', float('nan'))], []),
    ([valuation('2025-01-01', 10)] * 2, []),
    ([], [flow('2025-01-01', 0)]),
    ([], [flow('2025-01-01', True)]),
    ([], [flow('2025-01-01', 10)] * 2),
])
def test_invalid_or_ambiguous_records_rejected(rows, flows):
    with pytest.raises(ValueError):
        validate_tracking(rows, flows)


def test_correction_replaces_date_without_duplicate():
    rows = [valuation('2025-01-01', 100), valuation('2025-02-01', 110)]
    updated = upsert_valuation(rows, '2025-01-01', 105)
    assert len(updated) == 2 and updated[0]['total'] == 105
    assert rows[0]['total'] == 100


def test_old_dossier_migrates_and_new_tracking_survives_restore():
    frame = pd.DataFrame([['PEA', 'A', 100.]], columns=COLUMNS)
    old = json.loads(export_dossier({'real_snapshot': (frame, 50., date(2025, 1, 1))}))
    old['version'] = 1
    old.pop('valuations')
    old.pop('flows')
    loaded = import_dossier(json.dumps(old))
    assert loaded['version'] == 2
    assert loaded['valuations'] == [valuation('2025-01-01', 150)]
    loaded['valuations'].append(valuation('2025-02-01', 250))
    loaded['flows'] = [flow('2025-01-20', 100)]
    state = {'tracking_complete_old': True}
    restore_dossier(state, loaded)
    assert 'tracking_complete_old' not in state
    assert json.loads(export_dossier(state)) == loaded


def test_mismatched_snapshot_history_rejected_before_mutation():
    frame = pd.DataFrame([['PEA', 'A', 100.]], columns=COLUMNS)
    data = json.loads(export_dossier({'real_snapshot': (frame, 50., date(2025, 1, 1))}))
    data['valuations'][0]['total'] = 999
    state = {'external_flows': [flow('2025-01-01', 10)]}
    with pytest.raises(ValueError):
        restore_dossier(state, data)
    assert state == {'external_flows': [flow('2025-01-01', 10)]}


def test_ui_hides_results_until_confirmed_and_resets_on_new_flow():
    app = AppTest.from_file(str(ROOT / 'pages/suivi.py'))
    app.session_state.portfolio_valuations = [valuation('2025-01-01', 1000), valuation('2025-01-11', 1500)]
    app.session_state.external_flows = [flow('2025-01-06', 500)]
    app.run()
    assert not app.exception and len(app.metric) == 0
    app.checkbox[0].check().run()
    assert not app.exception
    assert app.metric[1].value == '0.00 €'
    assert app.metric[2].value == '0.00%'
    app.session_state.external_flows = [flow('2025-01-06', 400)]
    app.run()
    assert not app.exception
    assert not app.checkbox[0].value and len(app.metric) == 0


def test_ui_adds_deletes_flow_and_rejects_zero():
    app = AppTest.from_file(str(ROOT / 'pages/suivi.py')).run()
    app.button[0].click().run()
    assert len(app.error) == 1 and not app.exception
    app.number_input[0].set_value(200)
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state.external_flows[0]['amount'] == 200
    app.button[1].click().run()
    assert not app.exception
    assert app.session_state.external_flows == []


def test_positions_save_two_dates_and_correct_one():
    app = AppTest.from_file(str(ROOT / 'pages/positions_reelles.py')).run()
    app.date_input[0].set_value(date(2025, 1, 1))
    app.number_input[0].set_value(100)
    app.button[0].click().run()
    app.date_input[0].set_value(date(2025, 2, 1))
    app.number_input[0].set_value(200)
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state.portfolio_valuations == [valuation('2025-01-01', 100), valuation('2025-02-01', 200)]
    app.number_input[0].set_value(220)
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state.portfolio_valuations == [valuation('2025-01-01', 100), valuation('2025-02-01', 220)]
