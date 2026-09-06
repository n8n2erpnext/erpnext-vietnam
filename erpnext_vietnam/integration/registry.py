from __future__ import annotations

from erpnext_vietnam.integration.contracts import ComplianceAdapter

_REGISTRY: dict[str, ComplianceAdapter] = {}


def register(adapter: ComplianceAdapter) -> None:
    adapter_id = getattr(adapter, "adapter_id", "")
    channel = getattr(adapter, "channel", "")
    capabilities = getattr(adapter, "capabilities", frozenset())
    if not adapter_id or not channel or not capabilities:
        raise ValueError("Adapter must declare adapter_id, channel and capabilities")
    if adapter_id in _REGISTRY and _REGISTRY[adapter_id] is not adapter:
        raise ValueError(f"Adapter already registered: {adapter_id}")
    _REGISTRY[adapter_id] = adapter


def get_adapter(adapter_id: str) -> ComplianceAdapter:
    try:
        return _REGISTRY[adapter_id]
    except KeyError as exc:
        raise ValueError(f"Unknown compliance adapter: {adapter_id}") from exc


def registered_adapter_ids() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))
