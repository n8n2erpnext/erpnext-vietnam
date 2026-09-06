import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "erpnext_vietnam/einvoice/archive_uat.py").read_text()


class TestP4DArchiveUAT(unittest.TestCase):
    def test_uat_uses_existing_submitted_invoice_read_only(self):
        self.assertIn('frappe.get_doc("Sales Invoice", sales_invoice)', SOURCE)
        self.assertIn("invoice.docstatus != 1", SOURCE)
        self.assertNotIn("\n    invoice.save", SOURCE)
        self.assertNotIn("invoice.submit", SOURCE)

    def test_uat_proves_evidence_hash_file_hash_and_immutability(self):
        self.assertIn("acceptance_evidence_hash", SOURCE)
        self.assertIn("final_xml_sha256", SOURCE)
        self.assertIn("archive_snapshot_hash", SOURCE)
        self.assertIn("einvoice_archive_immutable", SOURCE)
        self.assertIn("submission_evidence_immutable", SOURCE)

    def test_uat_is_sandbox_rollback_only_and_cleans_physical_artifacts(self):
        self.assertIn('"sandbox.einvoice.v1"', SOURCE)
        self.assertIn("frappe.db.rollback()", SOURCE)
        self.assertIn("delete_file(file_url)", SOURCE)
        self.assertIn("os.remove(path)", SOURCE)
        self.assertIn("physical_artifacts_clean", SOURCE)
        self.assertNotIn("frappe.db.commit()", SOURCE)
        self.assertIn('"GL Entry"', SOURCE)
        self.assertIn('"Journal Entry"', SOURCE)


if __name__ == "__main__":
    unittest.main()
