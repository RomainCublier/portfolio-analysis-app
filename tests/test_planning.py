import json
import unittest
from core.planning import Project, export_project, import_project, project_path


class ProjectionTests(unittest.TestCase):
    def test_zero_return_is_exactly_contributions(self):
        end = project_path(Project(initial=1000, monthly=1000, years=20), 0)[-1]
        self.assertEqual(end["Capital simulé"], 241000)
        self.assertEqual(end["Gain / perte simulé(e)"], 0)

    def test_effective_annual_rate_and_fee(self):
        end = project_path(Project(initial=10000, monthly=0, years=1), .1, .01)[-1]
        self.assertAlmostEqual(end["Capital simulé"], 10890)

    def test_month_end_contributions_against_annuity_formula(self):
        rate = 1.06 ** (1 / 12) - 1
        expected = 200 * ((1 + rate) ** 24 - 1) / rate
        actual = project_path(Project(monthly=200, years=2), .06)[-1]["Capital simulé"]
        self.assertAlmostEqual(actual, expected)

    def test_loss_and_inflation(self):
        end = project_path(Project(initial=10000, monthly=0, years=1), -.2, inflation=.02)[-1]
        self.assertAlmostEqual(end["Gain / perte simulé(e)"], -2000)
        self.assertAlmostEqual(end["Capital en euros d’aujourd’hui"], 8000 / 1.02)

    def test_export_round_trip(self):
        p = Project(goal="Études", initial=500, monthly=70, years=4)
        self.assertEqual(import_project(export_project(p)), p)

    def test_reject_invalid_inputs(self):
        for value in (-1, float("nan"), float("inf"), True, "100"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                Project(initial=value)
        for value in (0, 51, 2.5):
            with self.assertRaises(ValueError):
                Project(years=value)
        for raw in ('[]', '{}', '{broken', 'x' * 20001):
            with self.assertRaises(ValueError):
                import_project(raw)
        for key, value in (("annual_return", -1), ("annual_fee", .11), ("inflation", float("nan"))):
            kwargs = {"annual_return": 0, key: value}
            with self.assertRaises(ValueError):
                project_path(Project(), **kwargs)


if __name__ == "__main__":
    unittest.main()
