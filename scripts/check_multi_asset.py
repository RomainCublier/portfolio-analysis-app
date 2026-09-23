"""Reproduce a two-asset 2022 research check. No live calls or implicit date selection."""
import argparse
import json
import pandas as pd
from pathlib import Path
from core.ishares_import import import_multi_asset_exports, import_bond_export, ISIN, BOND_ISIN
from core.history import buy_and_hold, path_metrics


def check(europe_raw, bond_raw, retrieved_at):
    levels, metadata, calendar, report = import_multi_asset_exports(
        europe_raw, bond_raw, retrieved_at, '2021-12-31', '2022-12-30')
    refs = json.loads((Path(__file__).resolve().parents[1] / 'data/research/annual_reference_returns.json').read_text())['series']
    reconciliation = {}
    for key in [ISIN, BOND_ISIN]:
        ref = next(r for r in refs if r['isin'] == key)
        if ref['currency'] != 'EUR' or ref['frequency'] != 'calendar_year':
            raise ValueError('Référence incompatible.')
        published = next(v['return_percent'] for v in ref['returns'] if v['year']==2022)
        calculated = float((levels[key].iloc[-1]/levels[key].iloc[0]-1)*100)
        tolerance = .5 * 10 ** -ref['published_decimal_places']
        if abs(calculated-published)>tolerance+1e-12:
            raise ValueError('Écart annuel supérieur à l’arrondi pour '+key)
        reconciliation[key] = dict(published_return_percent=published,calculated_return_percent=calculated,
            difference_percentage_points=calculated-published,rounding_tolerance_percentage_points=tolerance,
            source_url=ref['source_url'],independent_source=False)
    weights={ISIN:.6,BOND_ISIN:.4}  # Explicit engineering example, not profile-based advice.
    curve,_=buy_and_hold(levels,weights,metadata,calendar)
    final_values=levels.iloc[-1]/levels.iloc[0]*pd.Series(weights)
    report.update(retrieved_at=retrieved_at,weights=weights,metrics=path_metrics(curve),
        final_weights=(final_values/final_values.sum()).to_dict(),annual_reconciliation=reconciliation,
        period_reason='Période 2022 contrôlée après détection de lacunes en 2025 ; pas une sélection optimisant la performance.',
        limitations=['Exemple de calcul 60/40, pas une allocation personnalisée ou optimale.',
            'Sans versements ni rééquilibrage, frais de transaction ou fiscalité.',
            'VL et total return émetteur, pas des prix exécutables.',
            'Validation limitée à cette période et ces parts. Calendrier non vérifié indépendamment.',
            'Droits commerciaux non validés ; données brutes non publiées.'])
    try:
        import_bond_export(bond_raw,retrieved_at,'2024-12-31','2025-12-31')
        report['check_2025']={'status':'technical_import_passed_requires_separate_review'}
    except ValueError as exc:
        report['check_2025']={'status':'rejected','reason':str(exc)}
    return report


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('europe',type=Path);p.add_argument('bonds',type=Path)
    p.add_argument('--retrieved-at',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=check(a.europe.read_bytes(),a.bonds.read_bytes(),a.retrieved_at)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'observations':r['observations'],'metrics':r['metrics'],'reconciliation':r['annual_reconciliation'],'check_2025':r['check_2025']},ensure_ascii=False))
