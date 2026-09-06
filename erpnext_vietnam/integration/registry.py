from __future__ import annotations

from dataclasses import dataclass

from erpnext_vietnam.integration.certification import AdapterCertification, validate_certification
from erpnext_vietnam.integration.contracts import ComplianceAdapter


@dataclass(frozen=True, slots=True)
class AdapterRegistration:
    adapter: ComplianceAdapter
    certification: AdapterCertification | None = None


_REGISTRY: dict[str, AdapterRegistration] = {}


def register(adapter: ComplianceAdapter, certification: AdapterCertification | None = None) -> None:
    adapter_id = getattr(adapter, "adapter_id", "")
    channel = getattr(adapter, "channel", "")
    capabilities = getattr(adapter, "capabilities", frozenset())
    if not adapter_id or not channel or not capabilities:
        raise ValueError("Adapter must declare adapter_id, channel and capabilities")
    if certification:
        validate_certification(certification)
        if certification.adapter_id != adapter_id:
            raise ValueError("Adapter certification adapter_id does not match adapter")
        if certification.channel != channel:
            raise ValueError("Adapter certification channel does not match adapter")
    existing = _REGISTRY.get(adapter_id)
    if existing:
        if existing.adapter is not adapter:
            raise ValueError(f"Adapter already registered: {adapter_id}")
        if existing.certification != certification:
            raise ValueError(f"Adapter certification registration changed in-process: {adapter_id}")
        return
    _REGISTRY[adapter_id] = AdapterRegistration(adapter=adapter, certification=certification)


def get_registration(adapter_id: str) -> AdapterRegistration:
    try:
        return _REGISTRY[adapter_id]
    except KeyError as exc:
        raise ValueError(f"Unknown compliance adapter: {adapter_id}") from exc


def get_adapter(adapter_id: str) -> ComplianceAdapter:
    return get_registration(adapter_id).adapter


def require_production_certification(adapter_id: str, channel: str) -> AdapterCertification:
    registration = get_registration(adapter_id)
    certification = registration.certification
    if not certification:
        raise ValueError(f"Compliance adapter is not production-certified: {adapter_id}")
    validate_certification(certification)
    if certification.channel != channel:
        raise ValueError("Production adapter certification channel mismatch")
    return certification


def registered_adapter_ids() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))
