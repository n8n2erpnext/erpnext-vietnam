import json
import unittest
from decimal import Decimal
from pathlib import Path

from erpnext_vietnam.payroll.reconciliation_math import compare_amount, summarize_reconciliation

ROOT = Path(__file__).parents[1]


class TestP2Reconciliation(unittest.TestCase):
    def test_amount_comparison_uses_vnd_tolerance(self):
        self.assertEqual(compare_amount(100000, 100001, 1)["status"], "MATCH")
        self.assertEqual(compare_amount(100000, 100002, 1)["status"], "VARIANCE")

    def test_summary_prioritizes_unmapped_then_variance(self):
        rows = [
            {"code": "BHXH_EE", "expected": 800, "actual": 800, "status": "MATCH"},
            {"code": "PIT_WITHHOLDING", "expected": 100, "actual": 0, "status": "UNMAPPED"},
            {"code": "BHXH_ER", "expected": 1700, "actual": None, "status": "EXPECTED_ONLY"},
        ]
        result = summarize_reconciliation(rows)
        self.assertEqual(result["status"], "UNMAPPED")
        self.assertEqual(result["employee_expected_total"], Decimal("900"))
        self.assertEqual(result["employer_expected_total"], Decimal("1700"))

    def test_contribution_mapping_doctype(self):
        p = ROOT / "erpnext_vietnam/vietnam_localization/doctype/vn_contribution_component/vn_contribution_component.json"
        doc = json.loads(p.read_text())
        fields = {f["fieldname"]: f for f in doc["fields"]}
        self.assertEqual(doc["name"], "VN Contribution Component")
        self.assertIn("PIT_WITHHOLDING", fields["contribution_code"]["options"])
        self.assertIn("BHXH_ER", fields["contribution_code"]["options"])

    def test_payroll_payable_roles_are_semantic(self):
        source = (ROOT / "erpnext_vietnam/accounting/roles.py").read_text()
        for role in ("PIT_PAYABLE", "BHXH_PAYABLE", "BHYT_PAYABLE", "BHTN_PAYABLE"):
            self.assertIn(role, source)
        service = (ROOT / "erpnext_vietnam/payroll/reconciliation.py").read_text()
        self.assertIn("resolve_coa_mapping", service)
        self.assertNotIn('"3335"', service)
        self.assertNotIn('"3383"', service)
        self.assertNotIn('"3384"', service)
        self.assertNotIn('"3386"', service)

    def test_accrual_is_preview_only(self):
        source = (ROOT / "erpnext_vietnam/payroll/reconciliation.py").read_text()
        self.assertIn('"read_only": True', source)
        for forbidden in ('get_doc({"doctype": "Journal Entry"', "insert(ignore_permissions=True)", ".submit()", "make_gl_entries"):
            self.assertNotIn(forbidden, source)

    def test_standard_report_is_read_only(self):
        report = json.loads((ROOT / "erpnext_vietnam/vietnam_localization/report/vn_payroll_reconciliation/vn_payroll_reconciliation.json").read_text())
        self.assertEqual(report["report_type"], "Script Report")
        self.assertEqual(report["ref_doctype"], "Salary Slip")
        self.assertEqual(report["is_standard"], "Yes")


if __name__ == "__main__":
    unittest.main()
