from __future__ import annotations

from erpnext_vietnam.integration.contracts import (
    AcceptanceArtifact, AcceptanceEvidence, AmbiguousTransportError, SubmissionEnvelope, SubmissionResult,
)


class SandboxEInvoiceAdapter:
    adapter_id = "sandbox.einvoice.v1"
    channel = "E_INVOICE"
    capabilities = frozenset({"VALIDATE", "SUBMIT", "GET_STATUS", "RECONCILE"})

    def __init__(self):
        self.ledger: dict[str, str] = {}
        self.submit_calls: dict[str, int] = {}

    def reset(self) -> None:
        self.ledger.clear()
        self.submit_calls.clear()

    def validate(self, envelope: SubmissionEnvelope) -> None:
        if not envelope.payload_sha256 or not envelope.schema_version:
            raise ValueError("Sandbox envelope requires schema version and payload hash")

    def submit(self, envelope: SubmissionEnvelope) -> SubmissionResult:
        self.validate(envelope)
        key = envelope.idempotency_key
        self.submit_calls[key] = self.submit_calls.get(key, 0) + 1
        requested = str(envelope.payload.get("sandbox_outcome") or "ACCEPTED").upper()
        if key in self.ledger:
            return self._result(key, self.ledger[key], reused=True)
        final = "REJECTED" if requested == "REJECTED" else "ACCEPTED"
        self.ledger[key] = final
        if requested == "TIMEOUT":
            raise AmbiguousTransportError("Synthetic timeout after provider accepted the request")
        return self._result(key, final)

    def get_status(self, external_id: str) -> SubmissionResult:
        key = external_id.removeprefix("SBX-")
        status = self.ledger.get(key, "UNKNOWN")
        return self._result(key, status)

    def reconcile(self, envelope: SubmissionEnvelope) -> SubmissionResult:
        status = self.ledger.get(envelope.idempotency_key, "UNKNOWN")
        return self._result(envelope.idempotency_key, status)

    def _result(self, key: str, status: str, reused: bool = False) -> SubmissionResult:
        evidence = None
        if status == "ACCEPTED":
            final_xml = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                f'<SandboxEInvoice idempotency="{key}" status="ACCEPTED"/>'
            ).encode("utf-8")
            receipt = (
                '{"sandbox":true,"status":"ACCEPTED","idempotency_key":"' + key + '"}'
            ).encode("utf-8")
            evidence = AcceptanceEvidence(
                provider_document_id="SBX-INV-" + key[-12:],
                authority_code="SBX-AUTH-" + key[-10:],
                issued_at="2026-09-06 16:00:00",
                accepted_at="2026-09-06 16:00:01",
                signing_certificate_serial="SBX-CERT-0001",
                artifacts=(
                    AcceptanceArtifact("FINAL_XML", "sandbox-final.xml", final_xml, "application/xml"),
                    AcceptanceArtifact("RECEIPT", "sandbox-receipt.json", receipt, "application/json"),
                ),
                provider_response={"sandbox": True, "status": status, "idempotency_reused": reused},
            )
        return SubmissionResult(
            status=status,
            external_id="SBX-" + key,
            acknowledgement={"sandbox": True, "status": status, "idempotency_reused": reused},
            request_id="REQ-" + key[-12:],
            response_id="RES-" + key[-12:],
            http_status=200 if status == "ACCEPTED" else (422 if status == "REJECTED" else 202),
            evidence=evidence,
        )


sandbox_einvoice_adapter = SandboxEInvoiceAdapter()
