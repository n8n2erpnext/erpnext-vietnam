import unittest

from erpnext_vietnam.integration.contracts import AcceptanceArtifact, AcceptanceEvidence
from erpnext_vietnam.integration.evidence import (
    EvidenceValidationError, artifact_sha256, build_acceptance_snapshot, evidence_snapshot_hash,
)
from erpnext_vietnam.integration.adapters.sandbox import SandboxEInvoiceAdapter
from erpnext_vietnam.integration.contracts import SubmissionEnvelope


class TestP4DAcceptanceEvidence(unittest.TestCase):
    def test_snapshot_is_deterministic_and_hashes_artifact_bytes(self):
        evidence = AcceptanceEvidence(
            provider_document_id="DOC-1", authority_code="AUTH-1", accepted_at="2026-09-06 16:00:01",
            artifacts=(AcceptanceArtifact("FINAL_XML", "final.xml", b"<x/>", "application/xml"),),
            provider_response={"status": "accepted"},
        )
        snapshot = build_acceptance_snapshot(evidence, file_urls={"FINAL_XML": "/private/files/final.xml"})
        self.assertEqual(snapshot["artifacts"][0]["sha256"], artifact_sha256(b"<x/>"))
        self.assertEqual(snapshot["artifacts"][0]["file_url"], "/private/files/final.xml")
        self.assertEqual(evidence_snapshot_hash(snapshot), evidence_snapshot_hash(dict(snapshot)))

    def test_duplicate_roles_and_sensitive_response_keys_are_rejected(self):
        with self.assertRaises(EvidenceValidationError):
            build_acceptance_snapshot(AcceptanceEvidence(artifacts=(
                AcceptanceArtifact("RECEIPT", "a.json", b"{}"), AcceptanceArtifact("RECEIPT", "b.json", b"{}"),
            )))
        with self.assertRaises(EvidenceValidationError):
            build_acceptance_snapshot(AcceptanceEvidence(provider_response={"access_token": "do-not-store"}))

    def test_sandbox_reconcile_returns_normalized_evidence_after_timeout(self):
        adapter = SandboxEInvoiceAdapter()
        envelope = SubmissionEnvelope("E_INVOICE_ISSUE", "ACME", "v1", "KEY", "abc", {"sandbox_outcome": "TIMEOUT"})
        with self.assertRaises(Exception):
            adapter.submit(envelope)
        result = adapter.reconcile(envelope)
        self.assertEqual(result.status, "ACCEPTED")
        self.assertIsNotNone(result.evidence)
        roles = {a.role for a in result.evidence.artifacts}
        self.assertIn("FINAL_XML", roles)
        self.assertIn("RECEIPT", roles)
        self.assertTrue(all(a.filename.startswith("p4d-uat-") for a in result.evidence.artifacts))


if __name__ == "__main__":
    unittest.main()
