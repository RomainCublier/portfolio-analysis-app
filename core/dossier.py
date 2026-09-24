"""Portable user dossier; strict validation before any session mutation."""
from dataclasses import asdict
from datetime import date
import json
import math
from core.planning import Project, number
from core.catalog import valid_isin

COLUMNS = ['Compte', 'Support / ISIN', 'Valeur actuelle (€)']


def _date(value):
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value or parsed > date.today():
        raise ValueError('Date invalide ou future.')
    return parsed


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Clé JSON dupliquée.')
        result[key] = value
    return result


def validate(data):
    if not isinstance(data, dict) or set(data) != {'version', 'kind', 'project', 'allocation', 'snapshot', 'journal'}:
        raise ValueError('Structure du dossier invalide.')
    if type(data['version']) is not int or data['version'] != 1 or data['kind'] != 'investor_dossier':
        raise ValueError('Version du dossier non reconnue.')
    if data['project'] is not None:
        Project(**data['project'])
    weights = data['allocation']
    if not isinstance(weights, dict) or len(weights) > 200:
        raise ValueError('Allocation invalide.')
    for isin, weight in weights.items():
        if not valid_isin(isin):
            raise ValueError('ISIN invalide.')
        number(weight, 'Poids', 0, 1)
    if weights and not math.isclose(sum(weights.values()), 1, abs_tol=1e-8):
        raise ValueError('Les poids doivent totaliser 100 %.')
    snapshot = data['snapshot']
    if snapshot is not None:
        if set(snapshot) != {'date', 'cash', 'positions'}:
            raise ValueError('État des positions invalide.')
        _date(snapshot['date'])
        number(snapshot['cash'], 'Liquidités', 0, 100_000_000)
        if not isinstance(snapshot['positions'], list) or len(snapshot['positions']) > 1000:
            raise ValueError('Trop de positions.')
        for row in snapshot['positions']:
            if set(row) != set(COLUMNS) or row['Compte'] not in ['PEA', 'CTO']:
                raise ValueError('Compte ou colonnes invalides.')
            label = row['Support / ISIN']
            if not isinstance(label, str) or not label.strip() or len(label) > 200:
                raise ValueError('Support invalide.')
            number(row[COLUMNS[2]], 'Valorisation', 0, 100_000_000)
    if not isinstance(data['journal'], list) or len(data['journal']) > 500:
        raise ValueError('Journal invalide ou complet (500 entrées).')
    for entry in data['journal']:
        if set(entry) != {'date', 'note'}:
            raise ValueError('Entrée du journal invalide.')
        _date(entry['date'])
        if not isinstance(entry['note'], str) or not entry['note'].strip() or len(entry['note']) > 2000:
            raise ValueError('Note vide ou trop longue.')
    return data


def export_dossier(state):
    snapshot = state.get('real_snapshot')
    data = dict(version=1, kind='investor_dossier',
                project=asdict(state['project']) if state.get('project') else None,
                allocation=state.get('allocation_draft', {}),
                snapshot=None if snapshot is None else dict(positions=snapshot[0].to_dict('records'),
                    cash=snapshot[1], date=snapshot[2].isoformat()),
                journal=state.get('decision_journal', []))
    return json.dumps(validate(data), ensure_ascii=False, indent=2, allow_nan=False)


def import_dossier(raw):
    if len(raw) > 2_000_000:
        raise ValueError('Dossier trop volumineux.')
    try:
        return validate(json.loads(raw, object_pairs_hook=_unique))
    except (TypeError, KeyError, AttributeError, UnicodeError, OverflowError) as exc:
        raise ValueError('Dossier invalide.') from exc


def restore_dossier(state, data):
    import pandas as pd
    validate(data)
    project = Project(**data['project']) if data['project'] else None
    snap = data['snapshot']
    snapshot = None if snap is None else (pd.DataFrame(snap['positions'], columns=COLUMNS), snap['cash'], _date(snap['date']))
    for key in list(state):
        if key in {'project', 'allocation_draft', 'real_snapshot', 'real_positions', 'real_positions_editor', 'decision_journal', 'positions_revision'} or key.startswith(('allocation_', 'enable_', 'cap_', 'real_positions_editor_')):
            del state[key]
    if project:
        state['project'] = project
    if snapshot is not None:
        state['real_snapshot'] = snapshot
        state['real_positions'] = snapshot[0].copy()
    state['allocation_draft'] = dict(data['allocation'])
    state['decision_journal'] = list(data['journal'])
