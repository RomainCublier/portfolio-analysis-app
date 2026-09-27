"""Explicit adapter for the legacy WPEA issuer workbook, research only."""
import hashlib
import pandas as pd

from core.history import SeriesMetadata, validate_panel
from core.ishares_import import _sheets, _date, _number, import_bond_export, _combine_exports

ISIN = 'IE0002XZSHO1'
NAME = 'iShares MSCI World Swap PEA UCITS ETF'
SOURCE_URL = ('https://www.ishares.com/ch/professionals/en/products/335178/fund/1535604580403.ajax?'
              'fileType=xls&fileName=iShares-MSCI-World-Swap-PEA-UCITS-ETF-EUR-Acc_fund&dataType=fund')
HEADER = ['As Of', 'Currency', 'NAV per Share', 'Shares Outstanding', 'Total Net Assets',
          'Fund Return Series', 'Benchmark Return Series']


def import_wpea_export(raw, retrieved_at, start, end):
    sheets = _sheets(raw, {'Overview', 'Historical'})
    overview, history = sheets.get('Overview', []), sheets.get('Historical', [])
    if not overview or overview[0] != [NAME] or not history or history[0] != HEADER:
        raise ValueError('Structure WPEA inattendue.')
    facts = {}
    for row in overview:
        if len(row) == 2:
            if row[0] in facts:
                raise ValueError('Caractéristique WPEA répétée.')
            facts[row[0]] = row[1]
    if (facts.get('ISIN'), facts.get('Share Class Currency'), facts.get('Use of Income')) != (ISIN, 'EUR', 'Accumulating'):
        raise ValueError('Identité, devise ou capitalisation WPEA incompatible.')
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if any(pd.isna(d) or d.tz is not None or d != d.normalize() for d in [start, end]) or start >= end:
        raise ValueError('Période invalide.')
    dates, values = [], []
    for row in history[1:]:
        if not row:
            continue
        if len(row) != 7 or row[1] != 'EUR':
            raise ValueError('Ligne historique WPEA inattendue.')
        when = _date(row[0])
        _number(row[2])
        dates.append(when)
        value = None if row[5] in (None, '--', '-') else _number(row[5])
        if start <= when <= end and value is None:
            raise ValueError(f'Série de rendement WPEA absente au {when.date()}. Choisissez une période complète.')
        values.append(value)
    index = pd.DatetimeIndex(dates)
    if not index.is_unique or not index.is_monotonic_decreasing or start not in index or end not in index:
        raise ValueError('Dates WPEA dupliquées, désordonnées ou bornes exactes absentes.')
    series = pd.Series(values, index=index, dtype=float).sort_index().loc[start:end]
    levels = series.to_frame(ISIN)
    meta = {ISIN: SeriesMetadata(ISIN, 'EUR', SOURCE_URL, retrieved_at,
        str(_date(facts.get('Share Class launch date')).date()), 'net_total_return', 'fund',
        'unknown', '', hashlib.sha256(raw).hexdigest())}
    report = validate_panel(levels, meta, levels.index)
    report.update(commercial_ready=False, independently_verified_calendar=False,
                  calendar_basis='Dates de VL de la feuille Historical du même émetteur',
                  method='issuer_fund_return_series_v1', whole_workbook_validated=False,
                  parsed_sections=['Overview', 'Historical'], source_url=SOURCE_URL,
                  raw_sha256=meta[ISIN].raw_sha256)
    return levels, meta, levels.index, report


def import_wpea_bonds(stock_raw, bond_raw, retrieved_at, start, end):
    return _combine_exports(import_wpea_export(stock_raw, retrieved_at, start, end),
                            import_bond_export(bond_raw, retrieved_at, start, end))
