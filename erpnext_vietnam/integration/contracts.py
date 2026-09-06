from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class AmbiguousTransportError(RuntimeError):
    """The request may have reached the provider; reconcile before any retry."""


@dataclass(frozen=True, slots=True)
class SubmissionEnvelope:
    submission_type: str
    company: str
    schema_version: str
    idempotency_key: str
    payload_sha256: str
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class AcceptanceArtifact:
    role: str
    filename: str
    content: bytes
    media_type: str | None = None


@dataclass(frozen=True, slots=True)
class AcceptanceEvidence:
    provider_document_id: str | None = None
    authority_code: str | None = None
    issued_at: str | None = None
    accepted_at: str | None = None
    signing_certificate_serial: str | None = None
    artifacts: tuple[AcceptanceArtifact, ...] = ()
    provider_response: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class SubmissionResult:
    status: str
    external_id: str | None = None
    acknowledgement: dict[str, Any] | None = None
    request_id: str | None = None
    response_id: str | None = None
    http_status: int | None = None
    evidence: AcceptanceEvidence | None = None


class ComplianceAdapter(Protocol):
    adapter_id: str
    channel: str
    capabilities: frozenset[str]

    def validate(self, envelope: SubmissionEnvelope) -> None: ...
    def submit(self, envelope: SubmissionEnvelope) -> SubmissionResult: ...
    def get_status(self, external_id: str) -> SubmissionResult: ...
    def reconcile(self, envelope: SubmissionEnvelope) -> SubmissionResult: ...
