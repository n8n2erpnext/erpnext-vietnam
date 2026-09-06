from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any

from erpnext_vietnam.integration.contracts import AcceptanceArtifact, AcceptanceEvidence

EVIDENCE_SCHEMA = "VN-ACCEPTANCE-EVIDENCE-2026-01"
_ROLE_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,39}$")
_SENSITIVE_KEYS = {
    "password", "secret", "token", "access_token", "refresh_token", "api_key",
    "private_key", "client_secret", "credential", "credentials",
}


class EvidenceValidationError(ValueError):
    pass


def artifact_sha256(content: bytes) -> str:
    if not isinstance(content, (bytes, bytearray)):
        raise EvidenceValidationError("Acceptance artifact content must be bytes")
    return hashlib.sha256(bytes(content)).hexdigest()


def _validate_json_safe(value: Any, path: str = "provider_response") -> None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return
    if isinstance(value, list):
        for idx, item in enumerate(value):
            _validate_json_safe(item, f"{path}[{idx}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            if key_text.strip().lower() in _SENSITIVE_KEYS:
                raise EvidenceValidationError(f"Sensitive provider-response key is forbidden: {path}.{key_text}")
            _validate_json_safe(item, f"{path}.{key_text}")
        return
    raise EvidenceValidationError(f"Provider response is not JSON-safe at {path}")


def validate_acceptance_evidence(evidence: AcceptanceEvidence) -> None:
    roles: set[str] = set()
    for artifact in evidence.artifacts:
        role = str(artifact.role or "").upper()
        if not _ROLE_RE.fullmatch(role):
            raise EvidenceValidationError(f"Invalid acceptance artifact role: {artifact.role!r}")
        if role in roles:
            raise EvidenceValidationError(f"Duplicate acceptance artifact role: {role}")
        roles.add(role)
        if not artifact.filename or os.path.basename(artifact.filename) != artifact.filename:
            raise EvidenceValidationError("Acceptance artifact filename must be a basename")
        if not isinstance(artifact.content, (bytes, bytearray)) or not artifact.content:
            raise EvidenceValidationError(f"Acceptance artifact {role} must contain bytes")
    _validate_json_safe(evidence.provider_response)


def build_acceptance_snapshot(
    evidence: AcceptanceEvidence, *, file_urls: dict[str, str] | None = None
) -> dict[str, Any]:
    validate_acceptance_evidence(evidence)
    file_urls = {str(k).upper(): v for k, v in (file_urls or {}).items()}
    artifacts = []
    for artifact in evidence.artifacts:
        role = artifact.role.upper()
        item = {
            "role": role,
            "filename": artifact.filename,
            "sha256": artifact_sha256(artifact.content),
            "size": len(artifact.content),
            "media_type": artifact.media_type,
        }
        if file_urls.get(role):
            item["file_url"] = file_urls[role]
        artifacts.append(item)
    return {
        "schema": EVIDENCE_SCHEMA,
        "provider_document_id": evidence.provider_document_id,
        "authority_code": evidence.authority_code,
        "issued_at": evidence.issued_at,
        "accepted_at": evidence.accepted_at,
        "signing_certificate_serial": evidence.signing_certificate_serial,
        "artifacts": artifacts,
        "provider_response": evidence.provider_response or {},
    }


def evidence_snapshot_hash(snapshot: dict[str, Any]) -> str:
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
