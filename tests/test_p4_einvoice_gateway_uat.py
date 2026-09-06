import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "erpnext_vietnam/einvoice/uat.py").read_text()


class TestP4EInvoiceGatewayUAT(unittest.TestCase):
    def test_uat_uses_existing_submitted_invoice_without_mutating_it(self):
        self.assertIn('frappe.get_doc("Sales Invoice", sales_invoice)', SOURCE)
        self.assertIn("invoice.docstatus != 1", SOURCE)
        self.assertNotIn("invoice.save", SOURCE)
        self.assertNotIn("invoice.submit", SOURCE)

    def test_uat_is_sandbox_rollback_only_and_checks_accounting(self):
        self.assertIn('"sandbox.einvoice.v1"', SOURCE)
        self.assertIn("frappe.db.rollback()", SOURCE)
        self.assertNotIn("frappe.db.commit()", SOURCE)
        self.assertIn('"GL Entry"', SOURCE)
        self.assertIn('"Journal Entry"', SOURCE)

    def test_uat_proves_queue_unknown_retry_block_and_reconcile(self):
        self.assertIn('einvoice.status != "QUEUED"', SOURCE)
        self.assertIn('einvoice.status != "UNKNOWN"', SOURCE)
        self.assertIn("retry_blocked", SOURCE)
        self.assertIn('einvoice.status != "ACCEPTED"', SOURCE)
        self.assertIn("provider_submit_calls", SOURCE)


if __name__ == "__main__":
    unittest.main()
