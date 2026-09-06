import unittest
from decimal import Decimal

from erpnext_vietnam.declarations.adapters.vat_tt89_math import deductible_input_vat, derive_01_gtgt
from erpnext_vietnam.declarations.vat_reporting import aggregate_reporting_lines


class TestP3CVATMath(unittest.TestCase):
    def test_01_gtgt_formulas_are_deterministic(self):
        aggregated = {
            "23": 1_000_000, "24": 100_000, "23a": 200_000, "24a": 20_000,
            "26": 50_000, "29": 100_000, "30": 200_000, "31": 10_000,
            "32": 300_000, "33": 30_000, "32a": 40_000, "32b": 10_000, "34a": 70_000,
        }
        manual = {"22": 5_000, "37": 1_000, "38": 2_000, "39a": 3_000, "40b": 0, "42": 0}
        values, missing = derive_01_gtgt(aggregated, 80_000, manual)
        self.assertEqual(missing, [])
        self.assertEqual(values["27"], Decimal("630000"))
        self.assertEqual(values["28"], Decimal("40000"))
        self.assertEqual(values["34"], Decimal("750000"))
        self.assertEqual(values["36"], Decimal("-40000"))
        self.assertEqual(values["40a"], Decimal("0"))
        self.assertEqual(values["41"], Decimal("49000"))
        self.assertEqual(values["43"], Decimal("49000"))

    def test_missing_closing_inputs_do_not_get_invented(self):
        values, missing = derive_01_gtgt({}, 0, {})
        self.assertEqual(set(missing), {"22", "37", "38", "39a", "40b", "42"})
        self.assertIsNone(values["40a"])
        self.assertIsNone(values["43"])

    def test_deductible_input_vat_requires_explicit_status_and_ratio(self):
        lines = [
            {"doctype": "Purchase Invoice", "parent": "PI-1", "idx": 1, "tax_amount": 100, "input_vat_deduction_status": "Eligible", "input_vat_deductible_ratio": 100},
            {"doctype": "Purchase Invoice", "parent": "PI-1", "idx": 2, "tax_amount": 200, "input_vat_deduction_status": "Partially Eligible", "input_vat_deductible_ratio": 50},
            {"doctype": "Purchase Invoice", "parent": "PI-1", "idx": 3, "tax_amount": 300, "input_vat_deduction_status": "Non-deductible", "input_vat_deductible_ratio": 0},
        ]
        total, missing, _ = deductible_input_vat(lines)
        self.assertEqual(total, Decimal("200"))
        self.assertEqual(missing, [])

        _, missing, _ = deductible_input_vat([
            {"doctype": "Purchase Invoice", "parent": "PI-2", "idx": 1, "tax_amount": 100, "input_vat_deduction_status": "Unknown", "input_vat_deductible_ratio": 100}
        ])
        self.assertTrue(missing)

    def test_imported_input_is_total_and_subset(self):
        amounts, missing, warnings = aggregate_reporting_lines([{
            "doctype": "Purchase Invoice", "parent": "PI-1", "idx": 1,
            "reporting_value": 1_000, "tax_amount": 80,
            "reporting_category": {
                "value_indicator": "23", "tax_indicator": "24",
                "secondary_value_indicator": "23a", "secondary_tax_indicator": "24a",
                "requires_reduction_annex": False,
            },
        }])
        self.assertEqual(amounts["23"], Decimal("1000"))
        self.assertEqual(amounts["23a"], Decimal("1000"))
        self.assertEqual(amounts["24"], Decimal("80"))
        self.assertEqual(amounts["24a"], Decimal("80"))
        self.assertEqual(missing, [])
        self.assertEqual(warnings, [])

    def test_temporary_eight_percent_requires_annex(self):
        amounts, missing, warnings = aggregate_reporting_lines([{
            "doctype": "Sales Invoice", "parent": "SI-1", "idx": 1,
            "reporting_value": 1_000, "tax_amount": 80,
            "reporting_category": {
                "value_indicator": "32", "tax_indicator": "33",
                "secondary_value_indicator": None, "secondary_tax_indicator": None,
                "requires_reduction_annex": True,
            },
        }])
        self.assertEqual(amounts["32"], Decimal("1000"))
        self.assertEqual(amounts["33"], Decimal("80"))
        self.assertEqual(missing, [])
        self.assertTrue(warnings)



if __name__ == "__main__":
    unittest.main()
