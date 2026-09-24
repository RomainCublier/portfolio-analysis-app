"""Declared EUR valuations and external flows; no price inference."""
from datetime import date
import math
import re
from core.planning import number

SOURCE = 'https://www.gipsstandards.org/standards/gips-standards-for-firms/gips-standards-handbook-for-firms/'
MAX_TOTAL = 100_100_000_000  # 1,000 positions plus cash, each capped at EUR 100m


def parse_date(value):
    if not isinstance(value, str):
        raise ValueError('Date ISO attendue.')
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value or parsed > date.today():
        raise ValueError('Date invalide ou future.')
    return parsed


def validate_tracking(valuations, flows):
    if not isinstance(valuations, list) or len(valuations) > 1000:
        raise ValueError('Historique limité à 1 000 valorisations.')
    dates = set()
    for row in valuations:
        if not isinstance(row, dict) or set(row) != {'date', 'total'}:
            raise ValueError('Valorisation invalide.')
        parse_date(row['date'])
        number(row['total'], 'Valeur totale', 0, MAX_TOTAL)
        if row['date'] in dates:
            raise ValueError('Une seule valorisation est permise par date.')
        dates.add(row['date'])
    if not isinstance(flows, list) or len(flows) > 1000:
        raise ValueError('Historique limité à 1 000 mouvements.')
    identifiers = set()
    for flow in flows:
        if not isinstance(flow, dict) or set(flow) != {'id', 'date', 'amount', 'note'}:
            raise ValueError('Mouvement invalide.')
        if not isinstance(flow['id'], str) or not re.fullmatch(r'[0-9a-f]{32}', flow['id']) or flow['id'] in identifiers:
            raise ValueError('Identifiant de mouvement invalide ou dupliqué.')
        identifiers.add(flow['id'])
        parse_date(flow['date'])
        number(flow['amount'], 'Mouvement', -100_000_000, 100_000_000)
        if flow['amount'] == 0:
            raise ValueError('Un mouvement ne peut pas être nul.')
        if not isinstance(flow['note'], str) or len(flow['note']) > 200:
            raise ValueError('Libellé du mouvement trop long.')


def upsert_valuation(valuations, when, total):
    """Explicit same-date correction, never duplicate the observation."""
    updated = [dict(row) for row in valuations if row['date'] != when]
    updated.append({'date': when, 'total': total})
    validate_tracking(updated, [])
    return sorted(updated, key=lambda row: row['date'])


def session_valuations(state):
    """Include the legacy/current snapshot without discarding prior dates."""
    rows = state.get('portfolio_valuations', [])
    snapshot = state.get('real_snapshot')
    if snapshot is not None:
        positions, cash, when = snapshot
        total = float(positions['Valeur actuelle (€)'].sum()) + cash
        rows = upsert_valuation(rows, when.isoformat(), total)
    return rows


def period_result(start, end, flows, *, complete):
    """One Modified Dietz interval; flows at end of day, (start, end].

    No annualization, chaining, price interpolation, or GIPS compliance claim.
    Completeness includes a consistent set of accounts and all external flows.
    """
    if complete is not True:
        raise ValueError('Confirmez le périmètre et la liste complète des apports/retraits.')
    validate_tracking([start, end], flows)
    first, last = parse_date(start['date']), parse_date(end['date'])
    days = (last - first).days
    if days <= 0:
        raise ValueError('La date de fin doit suivre la date de début.')
    selected = [f for f in flows if first < parse_date(f['date']) <= last]
    details = [dict(f, weight=(last - parse_date(f['date'])).days / days) for f in selected]
    net = math.fsum(f['amount'] for f in selected)
    gain = end['total'] - start['total'] - net
    capital = start['total'] + math.fsum(f['amount'] * f['weight'] for f in details)
    reason = None
    if start['total'] <= 0:
        reason = 'Valeur initiale nulle : choisissez un début avec un portefeuille valorisé.'
    elif capital <= 0:
        reason = 'Capital pondéré nul ou négatif : le pourcentage ne peut pas être interprété.'
    estimate = None if reason else gain / capital
    if estimate is not None and (not math.isfinite(estimate) or estimate < -1):
        estimate = None
        reason = 'Estimation incohérente avec ce suivi sans levier : vérifiez les données et raccourcissez la période.'
    return {'method': 'modified_dietz_end_of_day_v1', 'source': SOURCE,
            'start': dict(start), 'end': dict(end), 'days': days,
            'net_external_flows': net, 'gain_loss_eur': gain,
            'weighted_capital': capital, 'estimated_return': estimate,
            'unavailable_reason': reason, 'flows': details,
            'completeness': 'user_confirmed_not_verified',
            'limitations': ['Déclarations utilisateur, non rapprochées avec un courtier.',
                'Estimation non annualisée, moins précise avec de gros flux et des marchés volatils.',
                'Frais et fiscalité reflétés seulement dans les valeurs saisies ; aucun ajustement ajouté.',
                'Ni TWR exact ni revendication de conformité GIPS.']}
