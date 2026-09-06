import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "p2_parallel_uat.py"


class TestP2UATHarness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text()

    def test_harness_is_generic(self):
        self.assertNotIn("LightBI", self.source)
        self.assertIn('parser.add_argument("--company", required=True)', self.source)
        self.assertIn('parser.add_argument("--site", required=True)', self.source)

    def test_harness_is_rollback_only(self):
        self.assertIn("frappe.db.rollback()", self.source)
        self.assertNotIn("frappe.db.commit()", self.source)

    def test_harness_guards_accounting_and_gateway_side_effects(self):
        self.assertIn('frappe.db.count("Journal Entry")', self.source)
        self.assertIn('frappe.db.count("GL Entry")', self.source)
        self.assertIn('frappe.db.count("VN Submission")', self.source)
        self.assertIn("assert during_counts == before_counts", self.source)

    def test_harness_exercises_real_hrms_submit_and_reconciliation(self):
        self.assertIn("slip.submit()", self.source)
        self.assertIn("reconcile_salary_slip(slip.name)", self.source)
        self.assertIn('assert recon["status"] == "MATCH"', self.source)


if __name__ == "__main__":
    unittest.main()
