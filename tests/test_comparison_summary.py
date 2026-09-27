import unittest
import pandas as pd

from core.model_history import comparison_summary
from core.planning import Project


class ComparisonSummaryTests(unittest.TestCase):
    def setUp(self):
        self.dates = pd.to_datetime(['2025-01-31', '2025-02-28', '2025-03-31'])
        self.flows = pd.Series([0., 100., 100.], index=self.dates)
        self.curves = pd.DataFrame({'60/40': [1000., 1100., 1200.], '90/10': [1000., 900., 950.]}, index=self.dates)
        self.table = pd.DataFrame([
            {'Répartition': '60/40', 'Total versé (€)': 1200., 'Valeur finale (€)': 1200., 'Gain / perte (€)': 0.},
            {'Répartition': '90/10', 'Total versé (€)': 1200., 'Valeur finale (€)': 950., 'Gain / perte (€)': -250.},
        ])
        self.project = Project(initial=1000., monthly=100., years=10)

    def test_contributions_are_separate_from_gains(self):
        result = comparison_summary(self.table, self.curves, self.flows, self.project, '60/40')
        self.assertEqual(result['gain'], 0)
        self.assertEqual(result['chart']['Argent versé'].tolist(), [1000, 1100, 1200])
        self.assertTrue(result['shorter_than_project'])
        self.assertEqual(result['days'], 59)

    def test_user_choice_is_preserved_even_when_it_loses(self):
        result = comparison_summary(self.table, self.curves, self.flows, self.project, '90/10')
        self.assertEqual(result['gain'], -250)
        self.assertEqual(result['final'], 950)
        self.assertEqual(result['chart']['Portefeuille fictif'].iloc[-1], 950)

    def test_missing_choice_or_misaligned_cash_flows_rejected(self):
        with self.assertRaises(ValueError):
            comparison_summary(self.table, self.curves, self.flows, self.project, '30/70')
        with self.assertRaises(ValueError):
            comparison_summary(self.table, self.curves, self.flows.iloc[1:], self.project, '60/40')
