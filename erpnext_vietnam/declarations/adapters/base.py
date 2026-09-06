from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from erpnext_vietnam.declarations.canonical import payload_hash


@dataclass
class AdapterResult:
    form_code: str
    adapter_version: str
    legal_source: str
    indicators: dict[str, Any] = field(default_factory=dict)
    rows: list[dict[str, Any]] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    source_refs: list[dict[str, Any]] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return not self.missing_required

    def as_dict(self) -> dict:
        payload = {
            "form_code": self.form_code,
            "adapter_version": self.adapter_version,
            "legal_source": self.legal_source,
            "indicators": self.indicators,
            "rows": self.rows,
            "missing_required": sorted(set(self.missing_required)),
            "warnings": sorted(set(self.warnings)),
            "source_refs": self.source_refs,
            "ready": self.ready,
        }
        payload["payload_hash"] = payload_hash(payload)
        return payload
