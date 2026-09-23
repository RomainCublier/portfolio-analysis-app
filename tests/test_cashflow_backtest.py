import numpy as np
import pandas as pd
import pytest
from core.history import SeriesMetadata, buy_and_hold
from core.cashflow_backtest import simulate_contributions, monthly_observation_dates


def inputs(values=None):
    d=pd.to_datetime(['2024-12-31','2025-01-31','2025-02-28'])
    l=pd.DataFrame(values if values is not None else {'A':[100.,80.,100.]},index=d)
    m={k:SeriesMetadata(k,'EUR','https://example.org/synthetic','2026-09-23','2020-01-01','net_total_return','synthetic','unknown','','a'*64) for k in l}
    return l,m,d


def test_contribution_is_not_return_and_first_loss_is_preserved():
    l,m,d=inputs();f=pd.Series([0.,100.,0.],index=d)
    ledger,_,r=simulate_contributions(l,{'A':1.},m,d,100.,f)
    # 100 loses 20, then 100 added; 180 grows 25% to 225.
    assert ledger.portfolio_value.tolist()==pytest.approx([100.,180.,225.])
    assert r['capital_paid']==200 and r['gain_loss']==pytest.approx(25.)
    assert r['time_weighted_metrics']['total_return']==pytest.approx(0.)
    assert r['time_weighted_metrics']['max_drawdown']==pytest.approx(-.2)


def test_rebalance_self_financing_and_timing():
    l,m,d=inputs({'A':[100.,200.,100.],'B':[100.,100.,100.]})
    w={'A':.5,'B':.5};f=pd.Series([0.,100.,0.],index=d)
    ledger,weights,r=simulate_contributions(l,w,m,d,100.,f,pd.DatetimeIndex([d[1]]))
    # Before flow 150; after flow A150/B100; rebalance A125/B125.
    assert ledger.portfolio_value.tolist()==pytest.approx([100.,250.,187.5])
    assert weights.loc[d[1]].tolist()==pytest.approx([.5,.5])
    assert ledger.rebalance_purchases_plus_sales.iloc[1]==pytest.approx(50.)
    assert r['time_weighted_metrics']['total_return']==pytest.approx(.125)


def test_no_flows_matches_existing_buy_and_hold():
    l,m,d=inputs({'A':[100.,200.,100.],'B':[100.,100.,110.]});w={'A':.6,'B':.4}
    ledger,_,_=simulate_contributions(l,w,m,d,1000.)
    curve,_=buy_and_hold(l,w,m,d)
    np.testing.assert_allclose(ledger.portfolio_value/1000.,curve)
    np.testing.assert_allclose(ledger.time_weighted_index,curve)


def test_flat_prices_only_accumulate_savings():
    l,m,d=inputs({'A':[100.,100.,100.]})
    ledger,_,r=simulate_contributions(l,{'A':1.},m,d,100.,pd.Series([0.,10.,20.],index=d))
    assert r['final_value']==130 and r['gain_loss']==0
    assert r['time_weighted_metrics']['total_return']==0


@pytest.mark.parametrize('values', [[1.,0.,0.],[0.,-1.,0.],[0.,float('nan'),0.]])
def test_invalid_flows_rejected(values):
    l,m,d=inputs()
    with pytest.raises(ValueError):simulate_contributions(l,{'A':1.},m,d,100.,pd.Series(values,index=d))


def test_invalid_dates_and_capital_rejected():
    l,m,d=inputs()
    for dates in [pd.DatetimeIndex([d[0]]),pd.DatetimeIndex([d[1],d[1]]),pd.to_datetime(['2025-01-30'])]:
        with pytest.raises(ValueError):simulate_contributions(l,{'A':1.},m,d,100.,rebalance_dates=dates)
    with pytest.raises(ValueError):simulate_contributions(l,{'A':1.},m,d,0.)
    with pytest.raises(ValueError):simulate_contributions(l,{'A':1.},m,d,100.,pd.Series([0.,1.],index=d[:2]))


def test_monthly_schedule_explicit_and_missing_month_rejected():
    _,_,d=inputs()
    assert monthly_observation_dates(d).equals(d[1:])
    with pytest.raises(ValueError,match='mois manquent'):monthly_observation_dates(d[[0,2]])


def test_ui_separates_savings_from_performance():
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    root=Path(__file__).resolve().parents[1]
    script='''
from pathlib import Path
from io import BytesIO
from unittest.mock import patch
import pandas as pd
from core.history import SeriesMetadata
root=Path(%r)
d=pd.to_datetime(['2024-12-31','2025-01-31','2025-02-28'])
l=pd.DataFrame({'A':[100.,100.,100.]},index=d)
m={'A':SeriesMetadata('A','EUR','https://example.org/synthetic','2026-09-23','2020-01-01','net_total_return','synthetic','unknown','','a'*64)}
r={'start':'2024-12-31','end':'2025-02-28'}
with patch('streamlit.file_uploader',return_value=BytesIO(b'fixture')), patch('core.history_import.import_history',return_value=(l,m,d,r)):
    exec(compile((root/'pages/backtest.py').read_text(),str(root/'pages/backtest.py'),'exec'),
         {'__file__':str(root/'pages/backtest.py')})
''' % str(root)
    app=AppTest.from_string(script).run()
    app.checkbox[0].check().run()
    app.number_input[0].set_value(100)
    app.number_input[2].set_value(100)
    app.selectbox[0].set_value('Mensuel')
    app.button[0].click().run()
    assert not app.exception
    assert [m.value for m in app.metric[:4]]==['1200.00 €','1200.00 €','0.00 €','0.00%']
    assert len(app.get('download_button'))==6
