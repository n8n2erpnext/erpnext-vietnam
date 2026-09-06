from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Any


@dataclass(frozen=True, slots=True)
class SubmissionEnvelope:
    submission_type: str
    company: str
    schema_version: str
    idempotency_key: str
    payload_sha256: str
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class SubmissionResult:
    status: str
    external_id: str | None = None
    acknowledgement: dict[str, Any] | None = None


class ComplianceAdapter(Protocol):
    def validate(self, envelope: SubmissionEnvelope) -> None: ...
    def submit(self, envelope: SubmissionEnvelope) -> SubmissionResult: ...
    def get_status(self, external_id: str) -> SubmissionResult: ...
    def reconcile(self, envelope: SubmissionEnvelope) -> SubmissionResult: ...
