"""Synthetic XML fixtures test the adapter; no market feed in CI."""
from xml.etree.ElementTree import Element, SubElement, tostring
import pytest
from core.ishares_import import import_europe_export, NS, ISIN, NAME
from core.history import buy_and_hold, path_metrics


def fixture(currency='EUR', extra='100', missing=False, duplicate=False, bad_fund_row=False):
    root = Element(f'{{{NS}}}Workbook')
    def sheet(name, rows):
        w = SubElement(root, f'{{{NS}}}Worksheet', {f'{{{NS}}}Name': name})
        table = SubElement(w, f'{{{NS}}}Table')
        for values in rows:
            row = SubElement(table, f'{{{NS}}}Row')
            for value in values:
                cell = SubElement(row, f'{{{NS}}}Cell')
                if value is not None:
                    SubElement(cell, f'{{{NS}}}Data').text = value
    sheet('Key Facts', [['ISIN',ISIN],['Share Class Currency',currency],['Use of Income','Accumulating'],['Inception Date','25/Sept/2009']])
    rows = [['Fri, 03 Jan 2025','99','110'], ['Thu, 02 Jan 2025','90','110'], ['Wed, 01 Jan 2025',extra,'110'], ['Tue, 31 Dec 2024','100','100']]
    if missing:rows.pop(1)
    if duplicate:rows.insert(1,rows[0])
    if bad_fund_row:rows.insert(1,[None,'999','110'])
    sheet('Growth of Hypothetical 10,000', [[None,NAME,'Index']]+rows+[[None,None,'111']])
    sheet('Historical NAVs', [[None,None,None,None,'Historical NAVs'], ['03/Jan/2025','99',None,None], ['02/Jan/2025','90'], ['31/Dec/2024','100']])
    return tostring(root)


def run(raw):return import_europe_export(raw,'2026-09-23','2024-12-31','2025-01-03')


def test_research_import_and_first_loss_preserved():
    levels, metadata, calendar, report = run(fixture())
    curve,_ = buy_and_hold(levels,{ISIN:1.},metadata,calendar)
    assert len(levels)==3
    assert path_metrics(curve)['total_return']==pytest.approx(-.01)
    assert path_metrics(curve)['max_drawdown']==pytest.approx(-.10)
    assert report['excluded_flat_non_nav_dates']==['2025-01-01']
    assert report['ignored_benchmark_only_rows']==1
    assert not report['commercial_ready'] and not report['independently_verified_calendar']
    with pytest.raises(ValueError,match='droits commerciaux'):
        buy_and_hold(levels,{ISIN:1.},metadata,calendar,commercial=True)


@pytest.mark.parametrize('kwargs', [dict(currency='USD'),dict(extra='101'),dict(missing=True),dict(duplicate=True),dict(bad_fund_row=True)])
def test_inconsistent_data_refused(kwargs):
    with pytest.raises(ValueError):run(fixture(**kwargs))


def test_exact_bounds_required_and_entities_refused():
    with pytest.raises(ValueError,match='Bornes'):
        import_europe_export(fixture(),'2026-09-23','2025-01-01','2025-01-03')
    with pytest.raises(ValueError,match='XML non autorisé'):
        run(b'<!DOCTYPE evil>'+fixture())


def test_issuer_upload_screen_computes_from_import():
    from pathlib import Path
    from datetime import date
    from streamlit.testing.v1 import AppTest
    root = Path(__file__).resolve().parents[1]
    script = '''
from pathlib import Path
from io import BytesIO
from unittest.mock import patch
root = Path(%r)
with patch('streamlit.file_uploader', return_value=BytesIO(%r)):
    exec(compile((root/'pages/backtest.py').read_text(),str(root/'pages/backtest.py'),'exec'),
         {'__file__':str(root/'pages/backtest.py')})
''' % (str(root), fixture())
    app = AppTest.from_string(script).run()
    app.radio[0].set_value('Export officiel iShares Europe').run()
    app.date_input[1].set_value(date(2025,1,3)).run()
    app.number_input[0].set_value(100)
    app.button[0].click().run()
    assert not app.exception
    assert app.metric[0].value == '-1.00%'
