"""Research adapter for one reviewed iShares XML export, never a generic XLS reader.

The growth series is total return, not a tradable execution price. Valuation dates
come from the separate NAV sheet in the same issuer file, not an independent calendar.
"""
from datetime import datetime
import hashlib
import math
import re
from xml.etree import ElementTree as ET
import pandas as pd
from core.history import SeriesMetadata, validate_panel

ISIN = 'IE00B4K48X80'
NAME = 'iShares Core MSCI Europe UCITS ETF EUR (Acc)'
SOURCE_URL = ('https://www.blackrock.com/varnish-api/uk-retail01-product-data/product-data/api/v1/get-fund-document?'
              'appSubType=ISHARES&appType=PRODUCT_PAGE&component=fundDownloadV2&locale=en_GB&'
              'portfolioId=251861&targetSite=ishares-uk&userType=individual')
NS = 'urn:schemas-microsoft-com:office:spreadsheet'
MONTHS = {m: i for i, m in enumerate(['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'], 1)}


def _date(value, growth=False):
    pattern = r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun), (\d{1,2}) ([A-Za-z]+) (\d{4})' if growth else r'(\d{1,2})/([A-Za-z]+)/([0-9]{4})'
    match = re.fullmatch(pattern, value or '')
    if not match:
        raise ValueError('Format de date iShares inattendu.')
    parts = match.groups()
    day, month, year = parts[-3:]
    month = 'Sep' if month == 'Sept' else month
    if month not in MONTHS:
        raise ValueError('Mois iShares inattendu.')
    result = pd.Timestamp(datetime(int(year), MONTHS[month], int(day)))
    if growth and ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][result.weekday()] != parts[0]:
        raise ValueError('Jour de semaine incohérent.')
    return result


def _number(value):
    if not re.fullmatch(r'(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?', value or ''):
        raise ValueError('Niveau iShares non numérique.')
    n = float(value.replace(',', ''))
    if not math.isfinite(n) or n <= 0:
        raise ValueError('Niveau iShares invalide.')
    return n


def _sheets(raw):
    if len(raw) > 5_000_000 or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('Export trop volumineux ou XML non autorisé.')
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError('Export XML iShares attendu, pas un fichier XLS binaire.') from exc
    result = {}
    for sheet in root.findall(f'{{{NS}}}Worksheet'):
        name = sheet.get(f'{{{NS}}}Name')
        if name in result:
            raise ValueError('Feuille répétée.')
        rows = []
        for row in sheet.findall(f'{{{NS}}}Table/{{{NS}}}Row'):
            cells = []
            for cell in row.findall(f'{{{NS}}}Cell'):
                index = int(cell.get(f'{{{NS}}}Index', len(cells) + 1))
                if not len(cells) < index <= 100:
                    raise ValueError('Position de cellule invalide.')
                cells.extend([None] * (index - len(cells) - 1))
                data = cell.find(f'{{{NS}}}Data')
                cells.append(data.text if data is not None else None)
            while cells and cells[-1] is None:
                cells.pop()
            rows.append(cells)
        result[name] = rows
    return result


def import_europe_export(raw, retrieved_at, start, end):
    sheets = _sheets(raw)
    required = {'Key Facts', 'Historical NAVs', 'Growth of Hypothetical 10,000'}
    if not required <= set(sheets):
        raise ValueError('Feuilles attendues absentes.')
    facts = {}
    for row in sheets['Key Facts']:
        if len(row) >= 2:
            if row[0] in facts:
                raise ValueError('Caractéristique répétée.')
            facts[row[0]] = row[1]
    if (facts.get('ISIN') != ISIN or facts.get('Share Class Currency') != 'EUR'
            or facts.get('Use of Income') != 'Accumulating'):
        raise ValueError('Part, devise ou capitalisation incompatible.')
    growth_rows = sheets['Growth of Hypothetical 10,000']
    if not growth_rows or growth_rows[0][:2] != [None, NAME]:
        raise ValueError('Identité de la courbe non confirmée.')
    growth, nav = [], []
    benchmark_only_rows = 0
    for row in growth_rows[1:]:
        if not row:
            continue
        if len(row) == 3 and row[0] is None and row[1] is None:
            _number(row[2])
            benchmark_only_rows += 1
            continue
        if len(row) != 3:
            raise ValueError('Ligne de courbe inattendue.')
        growth.append((_date(row[0], growth=True), _number(row[1])))
    nav_rows = sheets['Historical NAVs']
    if not nav_rows or [x for x in nav_rows[0] if x] != ['Historical NAVs']:
        raise ValueError('En-tête des VL inattendu.')
    for row in nav_rows[1:]:
        if not row:
            continue
        if len(row) == 1 and row[0].startswith('The figures shown relate to past performance.'):
            continue
        if len(row) != 2:
            raise ValueError('Ligne de VL inattendue.')
        nav.append((_date(row[0]), _number(row[1])))
    def series(rows):
        s = pd.Series([v for _, v in rows], index=pd.DatetimeIndex([d for d, _ in rows]), dtype=float)
        if len(s) < 2 or not s.index.is_unique or not s.index.is_monotonic_decreasing:
            raise ValueError('Dates source dupliquées ou ordre inattendu.')
        return s.sort_index()
    g, n = series(growth), series(nav)
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if any(d.tz is not None or d != d.normalize() for d in [start, end]) or start >= end:
        raise ValueError('Période invalide.')
    if start not in n.index or end not in n.index:
        raise ValueError('Bornes exactes absentes des VL ; aucun décalage implicite.')
    calendar = n.loc[start:end].index
    missing = calendar.difference(g.index)
    if len(missing):
        raise ValueError('Courbe absente sur certaines dates de VL.')
    extra = g.loc[start:end].index.difference(calendar)
    if any(g.loc[d] != g.shift(1).loc[d] for d in extra):
        raise ValueError('Variation de la courbe sur une date sans VL ; revue requise.')
    levels = g.loc[calendar].to_frame(ISIN)
    metadata = {ISIN: SeriesMetadata(ISIN, 'EUR', SOURCE_URL, retrieved_at,
        str(_date(facts.get('Inception Date')).date()), 'net_total_return', 'fund', 'unknown', '',
        hashlib.sha256(raw).hexdigest())}
    report = validate_panel(levels, metadata, calendar)
    report.update(source_url=SOURCE_URL, raw_sha256=metadata[ISIN].raw_sha256,
        calendar_basis='Dates de la feuille Historical NAVs du même export émetteur',
        independently_verified_calendar=False, excluded_flat_non_nav_dates=[str(d.date()) for d in extra],
        commercial_ready=False, ignored_benchmark_only_rows=benchmark_only_rows,
        method='issuer_growth_on_nav_dates_v1',
        return_basis_note='Courbe de rendement total émetteur ; frais du fonds incorporés. Pas un cours de transaction.')
    return levels, metadata, calendar, report
