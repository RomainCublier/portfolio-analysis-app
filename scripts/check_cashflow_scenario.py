"""Explicit illustrative savings scenarios on the previously reviewed 2022 pair."""
import argparse
import json
from pathlib import Path
import pandas as pd
from core.cashflow_backtest import simulate_contributions, monthly_observation_dates
from core.ishares_import import import_multi_asset_exports, ISIN, BOND_ISIN


def check(europe_raw, bond_raw, retrieved_at):
    l,m,d,provenance=import_multi_asset_exports(europe_raw,bond_raw,retrieved_at,'2021-12-31','2022-12-30')
    schedule=monthly_observation_dates(d)
    flows=pd.Series(0.,index=d);flows.loc[schedule]=1000.
    scenarios={}
    for name,dates in [('no_rebalance',pd.DatetimeIndex([])),('monthly_rebalance',schedule)]:
        _,_,report=simulate_contributions(l,{ISIN:.6,BOND_ISIN:.4},m,d,10000.,flows,dates)
        scenarios[name]=report
    return dict(purpose='Exemple technique : 10 000 EUR initiaux, 1 000 EUR par mois observé, poids cibles 60/40. Pas un profil conseillé.',
        retrieved_at=retrieved_at,provenance=provenance,scenarios=scenarios,
        schedule_policy='Dernier point observé du mois après le mois initial ; décembre 2022 inclus au dernier point.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('europe',type=Path);p.add_argument('bonds',type=Path)
    p.add_argument('--retrieved-at',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=check(a.europe.read_bytes(),a.bonds.read_bytes(),a.retrieved_at)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:{f:v[f] for f in ['capital_paid','final_value','gain_loss']} for k,v in r['scenarios'].items()}))
