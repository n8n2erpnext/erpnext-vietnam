import json
import unittest
from pathlib import Path

from erpnext_vietnam.einvoice.canonical import build_canonical_invoice, SCHEMA_VERSION
from erpnext_vietnam.einvoice.lifecycle import operation_idempotency_key, transition_allowed

ROOT = Path(__file__).resolve().parents[1]


class TestP4EInvoice(unittest.TestCase):
    def _source(self):
        return {
            "source": {"doctype": "Sales Invoice", "name": "SINV-0001", "docstatus": 1},
            "seller": {"legal_name": "Seller Co", "tax_id": "0100000001"},
            "buyer": {"legal_name": "Buyer Co", "tax_id": "0100000002"},
            "currency": "VND", "net_total": 100_000_000, "native_vat_total": 10_000_000,
            "grand_total": 110_000_000,
            "lines": [{
                "idx": 1, "item_code": "SERVICE", "description": "Service", "qty": 1, "uom": "Nos",
                "net_amount": 100_000_000, "vat_classification": "STD10", "vat_treatment": "STANDARD_10",
                "vat_rate": 10, "vat_snapshot_hash": "a" * 64, "vat_reporting_category": "DOMESTIC_10",
            }],
        }

    def test_canonical_ready_and_reconciled(self):
        payload = build_canonical_invoice(self._source())
        self.assertTrue(payload["ready"])
        self.assertEqual(payload["schema"], SCHEMA_VERSION)
        self.assertEqual(str(payload["vat_total"]), "10000000")
        self.assertEqual(payload["missing_required"], [])
        self.assertEqual(len(payload["payload_hash"]), 64)

    def test_canonical_fails_closed_when_vat_evidence_missing(self):
        source = self._source()
        source["lines"][0]["vat_snapshot_hash"] = None
        source["native_vat_total"] = 8_000_000
        payload = build_canonical_invoice(source)
        self.assertFalse(payload["ready"])
        self.assertIn("line[1].vat_snapshot_hash", payload["missing_required"])
        self.assertIn("vat_total_reconciliation", payload["missing_required"])

    def test_lifecycle_requires_reconciliation_after_unknown(self):
        self.assertTrue(transition_allowed("SUBMITTING", "UNKNOWN"))
        self.assertFalse(transition_allowed("UNKNOWN", "SUBMITTING"))
        self.assertTrue(transition_allowed("UNKNOWN", "ACCEPTED"))
        self.assertTrue(transition_allowed("UNKNOWN", "REJECTED"))

    def test_issue_idempotency_is_stable_and_revision_scoped(self):
        first = operation_idempotency_key("ACME", "SINV-1", "ISSUE", 1)
        self.assertEqual(first, operation_idempotency_key("ACME", "SINV-1", "issue", 1))
        self.assertNotEqual(first, operation_idempotency_key("ACME", "SINV-1", "ISSUE", 2))
        self.assertTrue(first.startswith("VN-EINV:"))

    def test_schema_is_provider_neutral_and_secret_free(self):
        for slug in ("vn_e_invoice", "vn_e_invoice_profile"):
            obj = json.loads((ROOT / "erpnext_vietnam/vietnam_localization/doctype" / slug / f"{slug}.json").read_text())
            text = json.dumps(obj).lower()
            self.assertNotIn("private_key", text)
            self.assertNotIn("api_secret", text)
            self.assertNotIn("password", text)
        profile = json.loads((ROOT / "erpnext_vietnam/vietnam_localization/doctype/vn_e_invoice_profile/vn_e_invoice_profile.json").read_text())
        fields = {f["fieldname"] for f in profile["fields"]}
        self.assertIn("endpoint", fields)
        self.assertIn("signing_reference", fields)

    def test_sales_invoice_hook_is_local_preparation_only(self):
        hooks = (ROOT / "erpnext_vietnam/hooks.py").read_text()
        events = (ROOT / "erpnext_vietnam/einvoice/events.py").read_text()
        self.assertIn("prepare_companion", events)
        self.assertNotIn("adapter.submit(", events)
        self.assertNotIn("requests.", events)
        self.assertIn('"Sales Invoice"', hooks)
        service = (ROOT / "erpnext_vietnam/einvoice/service.py").read_text()
        feature_gate = service.index("if require_feature_enabled:")
        preview_call = service.index("preview = preview_einvoice", feature_gate)
        self.assertLess(feature_gate, preview_call)


if __name__ == "__main__":
    unittest.main()
