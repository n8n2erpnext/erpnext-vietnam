import json
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]


class TestP2Schema(unittest.TestCase):
    def test_p2_doctypes_exist(self):
        for slug, name in {
            "vn_employee_tax_profile": "VN Employee Tax Profile",
            "vn_dependent": "VN Dependent",
            "vn_wage_region": "VN Wage Region",
            "vn_social_insurance_profile": "VN Social Insurance Profile",
            "vn_pit_bracket": "VN PIT Bracket",
            "vn_payroll_calculation_line": "VN Payroll Calculation Line",
        }.items():
            p = ROOT / f"erpnext_vietnam/vietnam_localization/doctype/{slug}/{slug}.json"
            self.assertTrue(p.exists(), slug)
            self.assertEqual(json.loads(p.read_text())["name"], name)

    def test_pit_2026_reference_values_are_seeded(self):
        seed = (ROOT / "erpnext_vietnam/setup/p2_seed.py").read_text()
        for value in ("15500000", "6200000", "10000000", "30000000", "60000000", "100000000"):
            self.assertIn(value, seed)
        for instrument in ("109/2025/QH15", "110/2025/UBTVQH15", "41/2024/QH15", "293/2025/NĐ-CP", "374/2025/NĐ-CP"):
            self.assertIn(instrument, seed)

    def test_reference_level_transition_is_effective_dated(self):
        seed = (ROOT / "erpnext_vietnam/setup/p2_seed.py").read_text()
        self.assertIn('"2026-01-01", 2340000', seed)
        self.assertIn('"2026-07-01", 2530000', seed)

    def test_hrms_remains_optional_and_salary_slip_hook_is_additive(self):
        hooks = (ROOT / "erpnext_vietnam/hooks.py").read_text()
        self.assertEqual(eval(next(x.split("=",1)[1].strip() for x in hooks.splitlines() if x.startswith("required_apps"))), ["erpnext"])
        self.assertIn('"Salary Slip": {', hooks)
        self.assertNotIn("override_doctype_class", hooks)

    def test_salary_component_fields_require_explicit_review(self):
        source = (ROOT / "erpnext_vietnam/setup/custom_fields.py").read_text()
        self.assertIn("vn_compliance_review_status", source)
        self.assertIn('"default": "Unreviewed"', source)
        for field in ("vn_pit_taxable", "vn_bhxh_base_included", "vn_bhyt_base_included", "vn_bhtn_base_included"):
            self.assertIn(field, source)

    def test_payroll_service_does_not_mutate_hrms_payroll_amounts(self):
        source = (ROOT / "erpnext_vietnam/payroll/service.py").read_text()
        for forbidden in ("make_salary_slip", "set_salary_structure_assignment", "make_gl_entries", "db_set(\"net_pay\"", "append(\"deductions\""):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
