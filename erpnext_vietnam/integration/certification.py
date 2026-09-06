from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

_CERT_KIND_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,39}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_CONTRACT_KINDS = {"TECHNICAL_CONTRACT", "API_SPEC"}
_REQUIRED_SCHEMA_KINDS = {"PAYLOAD_SCHEMA"}


class CertificationValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CertificationArtifact:
    kind: str
    source_ref: str
    version: str
    sha256: str


@dataclass(frozen=True, slots=True)
class AdapterCertification:
    adapter_id: str
    channel: str
    certification_version: str
    provider_name: str
    reviewed_on: str
    artifacts: tuple[CertificationArtifact, ...]
    status: str = "RELEASED"


def validate_certification(certification: AdapterCertification) -> None:
    if certification.status != "RELEASED":
        raise CertificationValidationError("Production certification must be RELEASED")
    for label, value in {
        "adapter_id": certification.adapter_id, "channel": certification.channel,
        "certification_version": certification.certification_version,
        "provider_name": certification.provider_name, "reviewed_on": certification.reviewed_on,
    }.items():
        if not str(value or "").strip():
            raise CertificationValidationError(f"Certification {label} is required")
    if not certification.artifacts:
        raise CertificationValidationError("Certification must pin official technical artifacts")
    seen = set()
    kinds = set()
    for artifact in certification.artifacts:
        kind = str(artifact.kind or "").upper()
        if not _CERT_KIND_RE.fullmatch(kind):
            raise CertificationValidationError(f"Invalid certification artifact kind: {artifact.kind!r}")
        if not str(artifact.source_ref or "").strip() or not str(artifact.version or "").strip():
            raise CertificationValidationError("Certification artifact source_ref and version are required")
        digest = str(artifact.sha256 or "").lower()
        if not _SHA256_RE.fullmatch(digest):
            raise CertificationValidationError(f"Certification artifact {kind} must have a SHA-256 digest")
        identity = (kind, artifact.source_ref.strip(), artifact.version.strip())
        if identity in seen:
            raise CertificationValidationError(f"Duplicate certification artifact: {identity}")
        seen.add(identity)
        kinds.add(kind)
    if not (kinds & _REQUIRED_CONTRACT_KINDS):
        raise CertificationValidationError("Certification must pin a TECHNICAL_CONTRACT or API_SPEC")
    if not (kinds & _REQUIRED_SCHEMA_KINDS):
        raise CertificationValidationError("Certification must pin a PAYLOAD_SCHEMA")


def certification_snapshot(certification: AdapterCertification) -> dict:
    validate_certification(certification)
    artifacts = sorted((
        {"kind": a.kind.upper(), "source_ref": a.source_ref.strip(), "version": a.version.strip(),
         "sha256": a.sha256.lower()} for a in certification.artifacts
    ), key=lambda a: (a["kind"], a["source_ref"], a["version"]))
    return {
        "schema": "VN-ADAPTER-CERTIFICATION-2026-01",
        "adapter_id": certification.adapter_id, "channel": certification.channel,
        "certification_version": certification.certification_version,
        "provider_name": certification.provider_name, "reviewed_on": certification.reviewed_on,
        "status": certification.status, "artifacts": artifacts,
    }


def certification_hash(certification: AdapterCertification) -> str:
    canonical = json.dumps(certification_snapshot(certification), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
