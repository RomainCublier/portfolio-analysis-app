"""Connect documented research histories to the illustrative portfolio journey."""
import pandas as pd
from dataclasses import asdict
import hashlib
import json

from core.history import validate_panel, path_metrics
from core.cashflow_backtest import simulate_contributions, monthly_observation_dates
from core.models import MODELS, model_weights


def comparison_summary(table, curves, flows, project, model):
    selected = table.loc[table['Répartition'] == model]
    if len(selected) != 1 or model not in curves:
        raise ValueError('Répartition absente ou dupliquée dans la comparaison.')
    if not flows.index.equals(curves.index) or len(curves) < 2:
        raise ValueError('Calendrier des versements incompatible.')
    paid = project.initial + flows.cumsum()
    row = selected.iloc[0]
    days = (curves.index[-1] - curves.index[0]).days
    return {
        'model': model,
        'paid': float(row['Total versé (€)']),
        'final': float(row['Valeur finale (€)']),
        'gain': float(row['Gain / perte (€)']),
        'days': days,
        'shorter_than_project': days / 365.25 < project.years,
        'chart': pd.DataFrame({'Portefeuille fictif': curves[model], 'Argent versé': paid}),
    }


def comparison_key(dataset, stock, bond, project):
    levels, metadata, calendar, report = dataset
    payload = {
        'method': 'model_comparison_no_rebalance_v1',
        'project': asdict(project), 'stock': stock, 'bond': bond,
        'models': MODELS,
        'levels': hashlib.sha256(levels.to_csv().encode()).hexdigest(),
        'calendar': [str(day) for day in calendar],
        'metadata': {key: asdict(value) for key, value in metadata.items()},
        'report': report,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def coverage(weights, dataset):
    if dataset is None:
        return sorted(weights), None
    levels, metadata, calendar, _ = dataset
    report = validate_panel(levels, metadata, calendar)
    return sorted(set(weights) - set(levels.columns)), report


def compare_models(dataset, stock, bond, catalog, project):
    levels, metadata, calendar, _ = dataset
    # Validate the entire import before selecting columns: never fix gaps here.
    validate_panel(levels, metadata, calendar)
    required = [stock, bond]
    if any(key not in levels for key in required):
        raise ValueError('Historique manquant pour un support choisi.')
    if any(metadata[key].origin != 'fund' for key in required):
        raise ValueError('Cette comparaison exige des historiques de fonds, sans proxy ni données synthétiques.')
    if project.initial <= 0:
        raise ValueError('Un capital de départ positif est nécessaire pour ce backtest. Modifiez votre projet pour le tester.')
    selected = levels[required].copy()
    selected_meta = {key: metadata[key] for key in required}
    contributions = pd.Series(0., index=calendar)
    contributions.loc[monthly_observation_dates(calendar)] = project.monthly
    rows, curves = [], {}
    for model in MODELS:
        weights = model_weights(model, stock, bond, catalog)
        ledger, _, report = simulate_contributions(selected, weights, selected_meta, calendar,
                                                  project.initial, contributions, pd.DatetimeIndex([]))
        metrics = path_metrics(ledger['time_weighted_index'])
        rows.append({'Répartition': model, 'Total versé (€)': report['capital_paid'],
                     'Valeur finale (€)': report['final_value'], 'Gain / perte (€)': report['gain_loss'],
                     'Performance hors effet des apports (%)': metrics['total_return'] * 100,
                     'Baisse maximale observée (%)': metrics['max_drawdown'] * 100})
        curves[model] = ledger['portfolio_value']
    return pd.DataFrame(rows), pd.DataFrame(curves), contributions
