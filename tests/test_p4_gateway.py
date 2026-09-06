import unittest
from pathlib import Path

from erpnext_vietnam.integration.adapters.sandbox import SandboxEInvoiceAdapter
from erpnext_vietnam.integration.contracts import AmbiguousTransportError, SubmissionEnvelope
from erpnext_vietnam.integration.registry import get_adapter, register, registered_adapter_ids

ROOT = Path(__file__).resolve().parents[1]


def envelope(outcome="ACCEPTED"):
    return SubmissionEnvelope(
        submission_type="E_INVOICE_ISSUE",
        company="ACME",
        schema_version="VN-EINVOICE-CANONICAL-2026-01",
        idempotency_key="VN:test-key",
        payload_sha256="a" * 64,
        payload={"sandbox_outcome": outcome},
    )


class TestP4Gateway(unittest.TestCase):
    def test_registry_is_explicit_and_rejects_unknown_adapter(self):
        adapter = SandboxEInvoiceAdapter()
        register(adapter)
        self.assertIs(get_adapter(adapter.adapter_id), adapter)
        self.assertIn(adapter.adapter_id, registered_adapter_ids())
        with self.assertRaisesRegex(ValueError, "Unknown compliance adapter"):
            get_adapter("python.path.from.database")

    def test_sandbox_timeout_is_ambiguous_and_reconcile_finds_provider_truth(self):
        adapter = SandboxEInvoiceAdapter()
        env = envelope("TIMEOUT")
        with self.assertRaises(AmbiguousTransportError):
            adapter.submit(env)
        self.assertEqual(adapter.submit_calls[env.idempotency_key], 1)
        reconciled = adapter.reconcile(env)
        self.assertEqual(reconciled.status, "ACCEPTED")
        self.assertEqual(adapter.submit_calls[env.idempotency_key], 1)

    def test_sandbox_idempotency_does_not_duplicate_provider_record(self):
        adapter = SandboxEInvoiceAdapter()
        env = envelope("ACCEPTED")
        first = adapter.submit(env)
        second = adapter.submit(env)
        self.assertEqual(first.external_id, second.external_id)
        self.assertTrue(second.acknowledgement["idempotency_reused"])
        self.assertEqual(len(adapter.ledger), 1)

    def test_orchestrator_gates_transport_and_unknown_retry(self):
        source = (ROOT / "erpnext_vietnam/integration/orchestrator.py").read_text()
        self.assertIn("VN Compliance Gateway is disabled for this Company", source)
        self.assertIn("Integration Endpoint is disabled", source)
        self.assertIn("Sandbox adapters cannot be used by a PRODUCTION endpoint", source)
        self.assertIn("UNKNOWN submission must be reconciled", source)
        self.assertIn('"RECONCILE"', source)
        for forbidden in ("requests.", "httpx.", "urllib.request"):
            self.assertNotIn(forbidden, source)

    def test_submission_attempt_audit_is_append_only(self):
        source = (ROOT / "erpnext_vietnam/vietnam_localization/doctype/vn_submission_attempt/vn_submission_attempt.py").read_text()
        self.assertIn("append-only and immutable", source)
        self.assertIn("cannot be deleted", source)
        submission = (ROOT / "erpnext_vietnam/vietnam_localization/doctype/vn_submission/vn_submission.py").read_text()
        self.assertIn('"UNKNOWN": {"ACCEPTED", "REJECTED", "CANCELLED"}', submission)
        self.assertNotIn('"UNKNOWN": {"READY"', submission)

    def test_production_endpoint_rejects_sandbox_adapter(self):
        source = (ROOT / "erpnext_vietnam/vietnam_localization/doctype/vn_integration_endpoint/vn_integration_endpoint.py").read_text()
        self.assertIn('self.environment == "PRODUCTION" and self.adapter.startswith("sandbox.")', source)


if __name__ == "__main__":
    unittest.main()
