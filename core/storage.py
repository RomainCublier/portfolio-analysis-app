"""Encrypted, per-identity dossier storage with optimistic concurrency."""
import hashlib
import json
import sqlite3
from contextlib import closing

from cryptography.fernet import Fernet

from core.dossier import import_dossier


def owner_id(issuer, subject):
    if not all(isinstance(value, str) and value.strip() for value in (issuer, subject)):
        raise ValueError("Identité de connexion incomplète.")
    return hashlib.sha256(json.dumps([issuer, subject]).encode()).hexdigest()


class ConflictError(ValueError):
    pass


class DossierStore:
    def __init__(self, path, key):
        self.cipher = Fernet(key)
        self.path = str(path)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS dossiers '
                       '(owner TEXT PRIMARY KEY, revision INTEGER NOT NULL, payload BLOB)')

    def load(self, owner):
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute('SELECT revision, payload FROM dossiers WHERE owner = ?', (owner,)).fetchone()
        if row is None:
            return 0, None
        revision, payload = row
        if payload is None:
            return revision, None
        envelope = json.loads(self.cipher.decrypt(payload))
        if envelope['owner'] != owner:
            raise ValueError('Dossier incompatible avec cette identité.')
        return revision, import_dossier(envelope['dossier'])

    def save(self, owner, raw, revision):
        import_dossier(raw)
        payload = self.cipher.encrypt(json.dumps({'owner': owner, 'dossier': raw}).encode())
        return self._write(owner, payload, revision)

    def delete(self, owner, revision):
        # Keep a revision tombstone so an old tab cannot recreate deleted data.
        return self._write(owner, None, revision)

    def _write(self, owner, payload, revision):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT revision FROM dossiers WHERE owner = ?', (owner,)).fetchone()
            if (row[0] if row else 0) != revision:
                raise ConflictError('Le dossier a changé dans une autre session. Rechargez sa version avant de continuer.')
            db.execute('INSERT INTO dossiers VALUES (?, ?, ?) ON CONFLICT(owner) DO UPDATE '
                       'SET revision = excluded.revision, payload = excluded.payload',
                       (owner, revision + 1, payload))
        return revision + 1
