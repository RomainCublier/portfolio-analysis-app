"""Explicit end-of-observation contributions and self-financing rebalancing.

Fractional total-return units, not an execution simulator. No withdrawals,
transaction costs, taxes or additional deduction of embedded fund expenses.
"""
import math
import numpy as np
import pandas as pd
from core.history import buy_and_hold, path_metrics


def monthly_observation_dates(calendar):
    """Last supplied observation of each month AFTER the initial month.

    Not a market calendar. A partial final month uses its last supplied date;
    callers must show the schedule. Missing intervening months are refused.
    """
    from core.history import _dates
    _dates(calendar)
    periods = calendar.to_period('M')
    expected = pd.period_range(periods[0], periods[-1], freq='M')
    if not periods.unique().equals(expected):
        raise ValueError('Un ou plusieurs mois manquent ; calendrier mensuel impossible.')
    return pd.DatetimeIndex([calendar[periods == p][-1] for p in expected[1:]])


def simulate_contributions(levels, weights, metadata, calendar, initial_capital,
                           contributions=None, rebalance_dates=None):
    _, report = buy_and_hold(levels, weights, metadata, calendar)
    if isinstance(initial_capital, bool) or not isinstance(initial_capital, (float, int)) or not math.isfinite(initial_capital) or initial_capital <= 0:
        raise ValueError('Capital initial strictement positif requis.')
    flows = pd.Series(0., index=calendar) if contributions is None else contributions.copy()
    if not isinstance(flows, pd.Series) or not flows.index.equals(calendar):
        raise ValueError('Les versements doivent correspondre exactement au calendrier.')
    if (not pd.api.types.is_numeric_dtype(flows.dtype) or pd.api.types.is_bool_dtype(flows.dtype)
            or not np.isfinite(flows.to_numpy(dtype=float)).all() or (flows < 0).any() or flows.iloc[0] != 0):
        raise ValueError('Versements finis positifs ou nuls ; le premier point est réservé au capital initial.')
    dates = pd.DatetimeIndex([]) if rebalance_dates is None else rebalance_dates
    if (not isinstance(dates, pd.DatetimeIndex) or not dates.is_unique or not dates.is_monotonic_increasing
            or dates.hasnans or dates.tz is not None or not dates.isin(calendar[1:]).all()):
        raise ValueError('Dates de rééquilibrage uniques, ordonnées et présentes après le premier point requises.')
    w = pd.Series(weights).reindex(levels.columns).to_numpy(dtype=float)
    positions = initial_capital * w  # Monetary value of each total-return sleeve.
    paid = float(initial_capital)
    twr = 1.
    records = []
    allocations = []
    for i, day in enumerate(calendar):
        previous = float(positions.sum())
        if i:
            positions *= (levels.iloc[i] / levels.iloc[i-1]).to_numpy(dtype=float)
        before_flow = float(positions.sum())
        if not np.isfinite(positions).all() or before_flow <= 0 or not math.isfinite(previous):
            raise ValueError('Valeurs calculées hors domaine numérique.')
        if i:
            twr *= before_flow / previous
        flow = float(flows.iloc[i])
        positions += flow * w  # New capital follows the fixed target, not current weights.
        paid += flow
        turnover = 0.
        if day in dates:
            target = positions.sum() * w
            turnover = float(np.abs(target - positions).sum())  # Purchases + sales, excluding deposits.
            positions = target
        value = float(positions.sum())
        if not all(math.isfinite(v) for v in [value, paid, twr, turnover]):
            raise ValueError('Valeurs calculées hors domaine numérique.')
        records.append([before_flow, flow, value, paid, value-paid, twr, turnover])
        allocations.append(positions / value)
    ledger = pd.DataFrame(records,index=calendar,columns=[
        'value_before_flow','contribution','portfolio_value','capital_paid','gain_loss',
        'time_weighted_index','rebalance_purchases_plus_sales'])
    realised_weights = pd.DataFrame(allocations,index=calendar,columns=levels.columns)
    report.update(method='end_of_observation_contributions_v1', commercial_ready=False, initial_capital=initial_capital,
        weights=weights, contributions={str(d.date()):float(v) for d,v in flows.items() if v},
        rebalance_dates=[str(d.date()) for d in dates],
        event_order=['market_return','contribution_at_target_weights','optional_rebalance_to_target'],
        contribution_total=float(flows.sum()), capital_paid=paid,final_value=value,gain_loss=value-paid,
        time_weighted_metrics=path_metrics(ledger['time_weighted_index']),
        final_weights=realised_weights.iloc[-1].to_dict(),
        limitations=['Unités fractionnaires de rendement total, pas des ordres exécutables.',
            'Sans retraits, fiscalité, spread, courtage ni délais de règlement.',
            'Frais des fonds déjà incorporés ; aucune seconde déduction.',
            'La performance TWR neutralise les apports ; ce n’est pas le TRI personnel.',
            'Pas de revendication de conformité ou certification GIPS.'])
    return ledger, realised_weights, report
