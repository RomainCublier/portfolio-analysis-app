import unittest
from dataclasses import replace

import pandas as pd

from core.history import SeriesMetadata
from core.model_history import comparison_key
from core.planning import Project


class ComparisonStateTests(unittest.TestCase):
    def setUp(self):
        days = pd.to_datetime(['2025-01-01', '2025-02-01'])
        levels = pd.DataFrame({'A': [100., 110.], 'B': [100., 101.]}, index=days)
        metadata = {key: SeriesMetadata(key, 'EUR', 'https://example.org/test', '2025-02-02',
            '2020-01-01', 'net_total_return', 'synthetic', 'unknown', '', 'a' * 64) for key in levels}
        self.dataset = (levels, metadata, days, {})
        self.project = Project(initial=1000)

    def key(self, dataset=None, project=None, stock='A'):
        return comparison_key(dataset or self.dataset, stock, 'B', project or self.project)

    def test_same_inputs_preserve_result_identity(self):
        self.assertEqual(self.key(), self.key(project=replace(self.project)))

    def test_changes_to_project_or_instrument_invalidate_result(self):
        before = self.key()
        for project in [replace(self.project, monthly=200), replace(self.project, initial=2000), replace(self.project, years=20)]:
            self.assertNotEqual(before, self.key(project=project))
        self.assertNotEqual(before, self.key(stock='C'))

    def test_prices_and_provenance_changes_invalidate_result(self):
        before = self.key()
        self.dataset[0].iloc[1, 0] = 111
        self.assertNotEqual(before, self.key())
        before = self.key()
        self.dataset[1]['A'] = replace(self.dataset[1]['A'], raw_sha256='b' * 64)
        self.assertNotEqual(before, self.key())
