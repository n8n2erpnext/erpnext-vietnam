from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


TREATMENT_RATES = {
    "NON_TAXABLE": Decimal("0"),
    "ZERO_RATE_0": Decimal("0"),
    "REDUCED_5": Decimal("5"),
    "TEMP_REDUCED_8": Decimal("8"),
    "STANDARD_10": Decimal("10"),
}


@dataclass(frozen=True, slots=True)
class VATClassificationDefinition:
    code: str
    treatment: str
    statutory_rate: Decimal
    effective_from: date
    effective_to: date | None = None
    temporary_reduction_eligible: bool = False
    rule_set: str | None = None
    legal_instrument: str | None = None
    legal_reference_detail: str | None = None

    def applies_on(self, when: date) -> bool:
        return self.effective_from <= when and (self.effective_to is None or when <= self.effective_to)


@dataclass(frozen=True, slots=True)
class VATResolution:
    classification_code: str
    treatment: str
    rate: Decimal
    base_treatment: str
    base_rate: Decimal
    temporary_rule_code: str | None
    rule_set: str | None
    snapshot_hash: str
