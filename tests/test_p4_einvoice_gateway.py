import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "erpnext_vietnam/einvoice/gateway.py").read_text()
JS = (ROOT / "erpnext_vietnam/vietnam_localization/doctype/vn_e_invoice/vn_e_invoice.js").read_text()


class TestP4EInvoiceGateway(unittest.TestCase):
    def test_bridge_is_manual_and_uses_vn_submission(self):
        self.assertIn("def queue_einvoice", SOURCE)
        self.assertIn("prepare_submission(", SOURCE)
        self.assertIn('source_doctype="VN E-Invoice"', SOURCE)
        self.assertIn('SUBMISSION_TYPE = "E_INVOICE_ISSUE"', SOURCE)

    def test_bridge_blocks_invalid_lifecycle_and_requires_ready_payload(self):
        self.assertIn('einvoice.status not in {"PREPARED", "QUEUED"}', SOURCE)
        self.assertIn('payload.get("ready") is not True', SOURCE)
        self.assertIn('einvoice.status != "QUEUED"', SOURCE)
        self.assertIn('einvoice.status not in {"UNKNOWN", "SUBMITTING"}', SOURCE)

    def test_bridge_has_no_network_or_auto_transport_hook(self):
        for forbidden in ("requests.", "httpx.", "urllib.request"):
            self.assertNotIn(forbidden, SOURCE)
        events = (ROOT / "erpnext_vietnam/einvoice/events.py").read_text()
        self.assertNotIn("submit_einvoice", events)
        self.assertNotIn("queue_einvoice", events)

    def test_ui_only_surfaces_explicit_actions_by_status(self):
        self.assertIn('frm.doc.status === "PREPARED"', JS)
        self.assertIn('frm.doc.status === "QUEUED"', JS)
        self.assertIn('["UNKNOWN", "SUBMITTING"]', JS)
        self.assertIn("Queue for Submission", JS)
        self.assertIn("Reconcile", JS)

    def test_profile_resolution_is_company_scoped(self):
        self.assertIn('filters={"company": einvoice.company, "enabled": 1}', SOURCE)
        self.assertIn("Exactly one enabled VN E-Invoice Profile", SOURCE)


if __name__ == "__main__":
    unittest.main()
