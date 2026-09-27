"""Reproduce the 2025 issuer-data research check, without a network call.

python -m scripts.check_ishares_europe FILE.xls --retrieved-at YYYY-MM-DD --output REPORT.json
The input is the original public issuer export. No raw prices are committed.
"""
import argparse
import json
from pathlib import Path
from core.ishares_import import import_europe_export, ISIN
from core.history import buy_and_hold, path_metrics


def check(raw, retrieved_at):
    levels, metadata, calendar, report = import_europe_export(raw, retrieved_at, '2024-12-31', '2025-12-31')
    curve, _ = buy_and_hold(levels, {ISIN: 1.}, metadata, calendar)
    metrics = path_metrics(curve)
    path = Path(__file__).resolve().parents[1] / 'data/research/annual_reference_returns.json'
    reference = next(s for s in json.loads(path.read_text())['series'] if s['isin'] == ISIN)
    if reference['currency'] != report['currency'] or reference['frequency'] != 'calendar_year':
        raise ValueError('Référence annuelle incompatible.')
    published = next(r['return_percent'] for r in reference['returns'] if r['year'] == 2025)
    difference = metrics['total_return'] * 100 - published
    tolerance = .5 * 10 ** -reference['published_decimal_places']
    if abs(difference) > tolerance + 1e-12:
        raise ValueError('Rendement hors intervalle d’arrondi de la référence publiée.')
    report.update(retrieved_at=retrieved_at, isin=ISIN, weights={ISIN:1.},
        backtest_method='buy_and_hold_no_flows_v1', metrics=metrics,
        reconciliation=dict(year=2025,published_return_percent=published,
            calculated_return_percent=metrics['total_return']*100,difference_percentage_points=difference,
            rounding_tolerance_percentage_points=tolerance,within_published_rounding=True,
            reference_source_url=reference['source_url'],independent_source=False),
        limitations=['Un seul ETF, une année ; aucune validation de stratégie ou allocation.',
            'Calendrier issu du même export ; aucun contrôle externe de complétude.',
            'Rendement total émetteur : pas un prix auquel tous les ordres auraient été exécutés.',
            'Sans versements, rééquilibrage, courtage, spread ou fiscalité.',
            'Droits commerciaux non validés. Export source conservé localement, non publié dans Git.'])
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    parser.add_argument('--retrieved-at',required=True)
    parser.add_argument('--output',required=True,type=Path)
    args = parser.parse_args()
    report = check(args.input.read_bytes(), args.retrieved_at)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(f"{report['observations']} observations ; rapprochement annuel conforme à l’arrondi publié.")
