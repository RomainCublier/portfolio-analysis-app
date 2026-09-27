from pathlib import Path
import sqlite3

import pytest
from cryptography.fernet import Fernet, InvalidToken
from streamlit.testing.v1 import AppTest

from core.dossier import export_dossier
from core.planning import Project
from core.storage import ConflictError, DossierStore, owner_id


def test_encrypted_roundtrip_and_account_isolation(tmp_path):
    path = tmp_path / 'data.sqlite3'
    key = Fernet.generate_key()
    store = DossierStore(path, key)
    alice = owner_id('issuer', 'alice')
    bob = owner_id('issuer', 'bob')
    raw = export_dossier({'project': Project(goal='Mon projet confidentiel')})
    assert store.save(alice, raw, 0) == 1
    assert DossierStore(path, key).load(alice)[1]['project']['goal'] == 'Mon projet confidentiel'
    assert store.load(bob) == (0, None)
    assert b'Mon projet confidentiel' not in path.read_bytes()
    with pytest.raises(InvalidToken):
        DossierStore(path, Fernet.generate_key()).load(alice)
    with sqlite3.connect(path) as db:
        db.execute('INSERT INTO dossiers SELECT ?, revision, payload FROM dossiers WHERE owner = ?', (bob, alice))
    with pytest.raises(ValueError):
        store.load(bob)


def test_conflicts_and_deletion_tombstone(tmp_path):
    store = DossierStore(tmp_path / 'data.sqlite3', Fernet.generate_key())
    raw = export_dossier({})
    owner = owner_id('issuer', 'alice')
    store.save(owner, raw, 0)
    with pytest.raises(ConflictError):
        store.save(owner, raw, 0)
    assert store.delete(owner, 1) == 2
    assert store.load(owner) == (2, None)
    with pytest.raises(ConflictError):
        store.save(owner, raw, 1)
    assert store.save(owner, raw, 2) == 3


def test_invalid_data_never_replaces_saved_dossier(tmp_path):
    store = DossierStore(tmp_path / 'data.sqlite3', Fernet.generate_key())
    owner = owner_id('issuer', 'alice')
    store.save(owner, export_dossier({}), 0)
    with pytest.raises(ValueError):
        store.save(owner, '{}', 1)
    assert store.load(owner)[0] == 1
    assert owner_id('issuer1', 'alice') != owner_id('issuer2', 'alice')
    with pytest.raises(ValueError):
        owner_id('issuer', None)


def test_unconfigured_account_page_keeps_download_available():
    root = Path(__file__).resolve().parents[1]
    app = AppTest.from_file(str(root / 'pages/dossier.py')).run()
    assert not app.exception
    assert any('pas encore disponible' in item.value for item in app.info)
