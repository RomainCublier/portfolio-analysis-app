import hashlib
import json
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from core.history_import import import_history
from core.history import buy_and_hold

ROOT = Path(__file__).resolve().parents[1]


def sample():
    return ((ROOT / 'data/examples/synthetic_history.csv').read_bytes(),
            json.loads((ROOT / 'data/examples/synthetic_manifest.json').read_text()))


def encode(manifest):
    return json.dumps(manifest).encode()


def test_import_calculation_and_no_commercial_self_approval():
    raw, manifest = sample()
    for m in manifest['series'].values():
        m.update(license_status='approved', license_reference='uploader assertion')
    levels, metadata, calendar, report = import_history(raw, encode(manifest))
    curve, _ = buy_and_hold(levels, {'SYNTHETIC_A': .6, 'SYNTHETIC_B': .4}, metadata, calendar)
    assert curve.iloc[-1] == pytest.approx(1.046)
    assert curve.iloc[0] == 1
    assert report['raw_sha256'] == hashlib.sha256(raw).hexdigest()
    assert not report['commercial_ready']
    assert all(m.license_status == 'unknown' for m in metadata.values())
    with pytest.raises(ValueError, match='droits commerciaux'):
        buy_and_hold(levels, {'SYNTHETIC_A': .6, 'SYNTHETIC_B': .4}, metadata, calendar, commercial=True)


@pytest.mark.parametrize('mutation,match', [
    ('hash', 'Empreinte'), ('missing', 'incomplet'), ('currency', 'devise'),
    ('raw_close', 'rendement total'), ('duplicate', 'répétés'),
    ('nan', 'manquantes'), ('ragged', 'longueur'), ('bad_date', 'AAAA'),
])
def test_rejects_bad_inputs(mutation, match):
    raw, m = sample()
    if mutation == 'hash':
        raw = raw.replace(b'110,95', b'111,95')
    elif mutation == 'missing':
        m['expected_dates'].insert(1, '2021-06-30')
    elif mutation == 'currency':
        m['series']['SYNTHETIC_A']['currency'] = 'USD'
    elif mutation == 'raw_close':
        m['series']['SYNTHETIC_A']['return_basis'] = 'close'
    else:
        raw = raw.replace(*{
            'duplicate': (b'SYNTHETIC_B', b'SYNTHETIC_A'),
            'nan': (b'110,95', b'NaN,95'),
            'ragged': (b'110,95', b'110,95,12'),
            'bad_date': (b'2021-12-31', b'2021/12/31'),
        }[mutation])
        for entry in m['series'].values():
            entry['raw_sha256'] = hashlib.sha256(raw).hexdigest()
    with pytest.raises(ValueError, match=match):
        import_history(raw, encode(m))


def test_repeated_json_keys_and_invalid_top_level():
    raw, _ = sample()
    for document in [b'{"schema_version":1,"schema_version":1}', b'null', b'[]']:
        with pytest.raises(ValueError):
            import_history(raw, document)


def test_empty_screen_does_not_invent_results():
    app = AppTest.from_file(str(ROOT / 'pages/backtest.py')).run()
    assert not app.exception
    assert not app.metric
    assert app.title[0].value == 'Explorer un historique'


def test_imported_history_screen_calculates_and_exports():
    script = '''
from pathlib import Path
from io import BytesIO
from unittest.mock import patch
root = Path(%r)
files = [BytesIO((root / 'data/examples/synthetic_history.csv').read_bytes()),
         BytesIO((root / 'data/examples/synthetic_manifest.json').read_bytes())]
with patch('streamlit.file_uploader', side_effect=files):
    exec(compile((root / 'pages/backtest.py').read_text(), str(root / 'pages/backtest.py'), 'exec'),
         {'__file__': str(root / 'pages/backtest.py')})
''' % str(ROOT)
    app = AppTest.from_string(script).run()
    assert not app.exception
    app.number_input[0].set_value(60)
    app.number_input[1].set_value(40)
    app.button[0].click().run()
    assert not app.exception
    assert app.metric[0].value == '4.60%'
    assert len(app.get('download_button')) == 4
