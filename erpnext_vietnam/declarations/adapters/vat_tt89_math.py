from __future__ import annotations

from decimal import Decimal
from typing import Any


def d(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


REPORTING_INDICATORS = (
    "23", "24", "23a", "24a", "26", "29", "30", "31", "32", "33", "32a", "32b", "34a"
)
MANUAL_CLOSING_INPUTS = ("22", "37", "38", "39a", "40b", "42")


def deductible_input_vat(lines: list[dict]) -> tuple[Decimal, list[str], list[str]]:
    total = Decimal("0")
    missing: list[str] = []
    warnings: list[str] = []
    for line in lines:
        if line.get("doctype") != "Purchase Invoice":
            continue
        tax = line.get("tax_amount")
        label = f"Purchase Invoice {line.get('parent')} row {line.get('idx')}"
        if tax is None:
            missing.append(f"{label}: exact native input VAT amount")
            continue
        tax = d(tax)
        if tax == 0:
            continue
        status = line.get("input_vat_deduction_status")
        ratio_raw = line.get("input_vat_deductible_ratio")
        if status in (None, "", "Unknown"):
            missing.append(f"{label}: input VAT deduction status")
            continue
        if status == "Non-deductible":
            continue
        if ratio_raw in (None, ""):
            missing.append(f"{label}: input VAT deductible ratio")
            continue
        ratio = d(ratio_raw)
        if ratio < 0 or ratio > 100:
            missing.append(f"{label}: valid input VAT deductible ratio 0..100")
            continue
        if status == "Eligible" and ratio != 100:
            missing.append(f"{label}: Eligible status requires 100% deductible ratio")
            continue
        if status == "Partially Eligible" and not (0 < ratio < 100):
            missing.append(f"{label}: Partially Eligible status requires ratio strictly between 0 and 100")
            continue
        if status not in {"Eligible", "Partially Eligible", "Non-deductible"}:
            missing.append(f"{label}: supported input VAT deduction status")
            continue
        total += tax * ratio / Decimal("100")
    return total, sorted(set(missing)), sorted(set(warnings))


def derive_01_gtgt(
    aggregated: dict[str, Any],
    deductible_vat: Any,
    manual_inputs: dict[str, Any] | None = None,
) -> tuple[dict[str, Decimal | None], list[str]]:
    values: dict[str, Decimal | None] = {key: d(aggregated.get(key)) for key in REPORTING_INDICATORS}
    values["25"] = d(deductible_vat)

    values["27"] = d(values["29"]) + d(values["30"]) + d(values["32"]) + d(values["32a"]) - d(values["32b"])
    values["28"] = d(values["31"]) + d(values["33"])
    values["34"] = d(values["26"]) + d(values["27"]) + d(values["34a"])
    values["35"] = d(values["28"])
    values["36"] = d(values["35"]) - d(values["25"])

    manual_inputs = manual_inputs or {}
    missing = [key for key in MANUAL_CLOSING_INPUTS if key not in manual_inputs or manual_inputs[key] is None]
    for key in MANUAL_CLOSING_INPUTS:
        values[key] = d(manual_inputs[key]) if key in manual_inputs and manual_inputs[key] is not None else None

    values["40a"] = values["40"] = values["41"] = values["43"] = None
    if not missing:
        balance = d(values["36"]) - d(values["22"]) + d(values["37"]) - d(values["38"]) - d(values["39a"])
        values["40a"] = max(balance, Decimal("0"))
        values["41"] = max(-balance, Decimal("0"))
        values["40"] = d(values["40a"]) - d(values["40b"])
        values["43"] = d(values["41"]) - d(values["42"])
    return values, missing
