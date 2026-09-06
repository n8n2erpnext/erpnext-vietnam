from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import date
from decimal import Decimal

from erpnext_vietnam.legal.models import EffectiveRule
from erpnext_vietnam.legal.resolver import snapshot_hash as legal_rule_snapshot_hash
from erpnext_vietnam.vat.models import TREATMENT_RATES, VATClassificationDefinition, VATResolution


class VATClassificationError(ValueError):
    pass


def _normalized_rate(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.000001"))


def validate_classification(definition: VATClassificationDefinition) -> None:
    if definition.treatment not in TREATMENT_RATES:
        raise VATClassificationError(f"unknown VAT treatment: {definition.treatment}")
    expected = TREATMENT_RATES[definition.treatment]
    if _normalized_rate(definition.statutory_rate) != _normalized_rate(expected):
        raise VATClassificationError(
            f"{definition.treatment} requires statutory rate {expected}, got {definition.statutory_rate}"
        )
    if definition.effective_to and definition.effective_to < definition.effective_from:
        raise VATClassificationError("effective_to cannot be before effective_from")
    if definition.temporary_reduction_eligible and definition.treatment != "STANDARD_10":
        raise VATClassificationError("temporary VAT reduction eligibility is only valid for STANDARD_10 base treatment")


def resolve_vat(
    definition: VATClassificationDefinition,
    when: date,
    temporary_reduction_rule: EffectiveRule | None = None,
) -> VATResolution:
    validate_classification(definition)
    if not definition.applies_on(when):
        raise VATClassificationError(f"classification {definition.code} is not effective on {when.isoformat()}")

    treatment = definition.treatment
    rate = definition.statutory_rate
    temp_rule_code = None
    temp_rule_hash = None
    if definition.temporary_reduction_eligible and temporary_reduction_rule and temporary_reduction_rule.applies_on(when):
        rate = Decimal(str(temporary_reduction_rule.value))
        if rate != Decimal("8"):
            raise VATClassificationError(f"temporary VAT reduction rule must resolve to 8, got {rate}")
        treatment = "TEMP_REDUCED_8"
        temp_rule_code = temporary_reduction_rule.code
        temp_rule_hash = legal_rule_snapshot_hash(temporary_reduction_rule)

    payload = {
        "classification": asdict(definition),
        "resolved_treatment": treatment,
        "resolved_rate": str(rate),
        "temporary_rule_code": temp_rule_code,
        "temporary_rule_hash": temp_rule_hash,
    }
    payload["classification"]["effective_from"] = definition.effective_from.isoformat()
    payload["classification"]["effective_to"] = definition.effective_to.isoformat() if definition.effective_to else None
    payload["classification"]["statutory_rate"] = str(definition.statutory_rate)
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return VATResolution(
        classification_code=definition.code,
        treatment=treatment,
        rate=rate,
        base_treatment=definition.treatment,
        base_rate=definition.statutory_rate,
        temporary_rule_code=temp_rule_code,
        rule_set=definition.rule_set,
        snapshot_hash=hashlib.sha256(raw).hexdigest(),
    )
