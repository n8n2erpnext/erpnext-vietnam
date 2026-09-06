import unittest
from pathlib import Path


class TestP3DUATHarness(unittest.TestCase):
    def setUp(self):
        self.source = Path("erpnext_vietnam/declarations/uat.py").read_text()

    def test_harness_is_transactional_and_rollback_only(self):
        self.assertIn("frappe.db.rollback()", self.source)
        self.assertNotIn("frappe.db.commit()", self.source)
        self.assertIn('"GL Entry"', self.source)
        self.assertIn('"Journal Entry"', self.source)
        self.assertIn('"VN Submission"', self.source)

    def test_harness_exercises_persisted_ready_documents_and_export_hash_gate(self):
        self.assertIn('"VN Tax Declaration"', self.source)
        self.assertIn('"VN Social Insurance Export"', self.source)
        self.assertIn("_load_ready_adapter_document", self.source)
        self.assertIn("build_review_export", self.source)
        self.assertIn("rollback_clean", self.source)

    def test_harness_is_company_parameterized(self):
        self.assertIn("def run_review_export_uat(company: str)", self.source)
        self.assertNotIn("LightBI Inc", self.source)


if __name__ == "__main__":
    unittest.main()
