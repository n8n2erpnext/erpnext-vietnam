import unittest
from decimal import Decimal

from erpnext_vietnam.payroll.insurance_math import clamp_contribution_base, contribution_amount
from erpnext_vietnam.payroll.pit_math import progressive_tax, resident_assessable_income


class TestP2PayrollMath(unittest.TestCase):
    def setUp(self):
        self.brackets = [
            {"sequence": 1, "lower_bound": 0, "upper_bound": 10_000_000, "rate_percent": 5},
            {"sequence": 2, "lower_bound": 10_000_000, "upper_bound": 30_000_000, "rate_percent": 10},
            {"sequence": 3, "lower_bound": 30_000_000, "upper_bound": 60_000_000, "rate_percent": 20},
            {"sequence": 4, "lower_bound": 60_000_000, "upper_bound": 100_000_000, "rate_percent": 30},
            {"sequence": 5, "lower_bound": 100_000_000, "upper_bound": None, "rate_percent": 35},
        ]

    def test_progressive_boundaries(self):
        self.assertEqual(progressive_tax(10_000_000, self.brackets), Decimal("500000"))
        self.assertEqual(progressive_tax(30_000_000, self.brackets), Decimal("2500000"))
        self.assertEqual(progressive_tax(60_000_000, self.brackets), Decimal("8500000"))
        self.assertEqual(progressive_tax(100_000_000, self.brackets), Decimal("20500000"))

    def test_research_example_30m_salary(self):
        insurance = Decimal("2400000") + Decimal("450000") + Decimal("300000")
        assessable = resident_assessable_income(30_000_000, insurance, 15_500_000, 0)
        self.assertEqual(assessable, Decimal("11350000"))
        self.assertEqual(progressive_tax(assessable, self.brackets), Decimal("635000"))

    def test_bhxh_reference_ceiling_after_july_2026(self):
        self.assertEqual(clamp_contribution_base(100_000_000, 2_530_000, 50_600_000), Decimal("50600000"))
        self.assertEqual(contribution_amount(50_600_000, 8), Decimal("4048000"))

    def test_bhtn_region_i_ceiling(self):
        self.assertEqual(clamp_contribution_base(200_000_000, 5_310_000, 106_200_000), Decimal("106200000"))
        self.assertEqual(contribution_amount(106_200_000, 1), Decimal("1062000"))


if __name__ == "__main__":
    unittest.main()
