"""Synthetic workbook fixtures, never presented as market observations."""
import unittest
from xml.etree.ElementTree import Element, SubElement, tostring

from core.ishares_import import NS
from core.wpea_import import ISIN, NAME, HEADER, import_wpea_export


def fixture(missing=False, currency='EUR', isin=ISIN):
    root = Element(f'{{{NS}}}Workbook')
    sheets = {
        'Overview': [[NAME], ['ISIN', isin], ['Share Class Currency', currency],
                     ['Use of Income', 'Accumulating'], ['Share Class launch date', '26/Mar/2024']],
        'Historical': [HEADER,
            ['03/Jan/2025', currency, '5', '1', '5', '--', '100'],
            ['02/Jan/2025', currency, '5', '1', '5', '--' if missing else '101', '100'],
            ['31/Dec/2024', currency, '5', '1', '5', '100', '100']],
    }
    for name, rows in sheets.items():
        sheet = SubElement(root, f'{{{NS}}}Worksheet', {f'{{{NS}}}Name': name})
        table = SubElement(sheet, f'{{{NS}}}Table')
        for values in rows:
            row = SubElement(table, f'{{{NS}}}Row')
            for value in values:
                cell = SubElement(row, f'{{{NS}}}Cell')
                SubElement(cell, f'{{{NS}}}Data').text = value
    return tostring(root)


class WpeaImportTests(unittest.TestCase):
    def run_import(self, raw, end='2025-01-02'):
        return import_wpea_export(raw, '2026-09-26', '2024-12-31', end)

    def test_complete_interval_uses_fund_series_not_nav(self):
        levels, metadata, _, report = self.run_import(fixture())
        self.assertEqual(levels[ISIN].tolist(), [100, 101])
        self.assertEqual(metadata[ISIN].currency, 'EUR')
        self.assertFalse(report['commercial_ready'])

    def test_missing_return_inside_interval_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'absente'):
            self.run_import(fixture(missing=True))
        with self.assertRaisesRegex(ValueError, 'absente'):
            self.run_import(fixture(), '2025-01-03')

    def test_identity_and_currency_are_mandatory(self):
        for raw in (fixture(currency='USD'), fixture(isin='IE00B4L5Y983')):
            with self.assertRaises(ValueError):
                self.run_import(raw)

    def test_exact_dates_and_xml_safety(self):
        with self.assertRaises(ValueError):
            self.run_import(fixture(), '2025-01-01')
        with self.assertRaises(ValueError):
            self.run_import(b'<!DOCTYPE x>' + fixture())
