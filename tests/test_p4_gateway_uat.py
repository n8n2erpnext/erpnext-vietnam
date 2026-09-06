import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "erpnext_vietnam/integration/uat.py").read_text()


class TestP4GatewayUAT(unittest.TestCase):
    def test_uat_is_company_parameterized_and_rollback_only(self):
        self.assertIn("def run_gateway_rollback_uat(company: str)", SOURCE)
        self.assertIn("frappe.db.rollback()", SOURCE)
        self.assertNotIn("frappe.db.commit()", SOURCE)

    def test_uat_proves_timeout_reconcile_and_no_duplicate_submit(self):
        self.assertIn('submission.status != "UNKNOWN"', SOURCE)
        self.assertIn("retry_blocked", SOURCE)
        self.assertIn('submission.status != "ACCEPTED"', SOURCE)
        self.assertIn("provider_submit_calls", SOURCE)
        self.assertIn('"GL Entry"', SOURCE)
        self.assertIn('"Journal Entry"', SOURCE)

    def test_uat_uses_sandbox_only(self):
        self.assertIn('"sandbox.einvoice.v1"', SOURCE)
        for forbidden in ("requests.", "httpx.", "urllib.request", "PRODUCTION"):
            self.assertNotIn(forbidden, SOURCE)


if __name__ == "__main__":
    unittest.main()
