from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class LegalReference:
    instrument: str
    article: str | None = None
    official_url: str | None = None


@dataclass(frozen=True, slots=True)
class EffectiveRule:
    code: str
    effective_from: date
    effective_to: date | None
    value: Decimal | str | int | bool | dict[str, Any]
    priority: int = 100
    status: str = "Released"
    references: tuple[LegalReference, ...] = field(default_factory=tuple)

    def applies_on(self, when: date) -> bool:
        return self.status == "Released" and self.effective_from <= when and (self.effective_to is None or when <= self.effective_to)
