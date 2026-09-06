from __future__ import annotations

from decimal import Decimal

from erpnext_vietnam.declarations.canonical import payload_hash

VALID_DIRECTIONS = {"Output", "Input"}
VALID_TREATMENT_CONSTRAINTS = {
    "ANY_REVIEW", "NON_TAXABLE", "ZERO_RATE_0", "REDUCED_5", "STANDARD_10", "TEMP_REDUCED_8"
}


def d(value) -> Decimal:
    return Decimal(str(value or 0))


def resolve_reporting_category(name: str, direction: str, when, treatment: str | None = None) -> dict:
    import frappe
    from frappe.utils import getdate

    if direction not in VALID_DIRECTIONS:
        raise ValueError(f"invalid VAT reporting direction: {direction}")
    doc = frappe.get_doc("VN VAT Reporting Category", name)
    if doc.reporting_status != "Released":
        frappe.throw(f"VN VAT Reporting Category {name} is not Released")
    when = getdate(when)
    if getdate(doc.effective_from) > when or (doc.effective_to and getdate(doc.effective_to) < when):
        frappe.throw(f"VN VAT Reporting Category {name} is not effective on {when}")
    if doc.direction != direction:
        frappe.throw(f"VN VAT Reporting Category {name} is {doc.direction}, expected {direction}")
    constraint = doc.treatment_constraint or "ANY_REVIEW"
    if constraint != "ANY_REVIEW":
        if not treatment:
            frappe.throw(f"VN VAT Reporting Category {name} requires an explicit VAT treatment {constraint}")
        if constraint != treatment:
            frappe.throw(
                f"VN VAT Reporting Category {name} requires treatment {constraint}, got {treatment}"
            )
    payload = {
        "code": doc.code,
        "direction": doc.direction,
        "value_indicator": doc.value_indicator or None,
        "tax_indicator": doc.tax_indicator or None,
        "secondary_value_indicator": doc.secondary_value_indicator or None,
        "secondary_tax_indicator": doc.secondary_tax_indicator or None,
        "treatment_constraint": constraint,
        "requires_reduction_annex": bool(doc.requires_reduction_annex),
        "effective_from": str(doc.effective_from),
        "effective_to": str(doc.effective_to) if doc.effective_to else None,
        "rule_set": doc.rule_set or None,
        "legal_instrument": doc.legal_instrument or None,
        "legal_reference_detail": doc.legal_reference_detail or None,
    }
    payload["snapshot_hash"] = payload_hash(payload)
    return payload


def aggregate_reporting_lines(lines: list[dict]) -> tuple[dict[str, Decimal], list[str], list[str]]:
    indicators: dict[str, Decimal] = {}
    missing: list[str] = []
    warnings: list[str] = []
    for line in lines:
        category = line.get("reporting_category") or {}
        if not category:
            missing.append(
                f"{line.get('doctype')} {line.get('parent')} row {line.get('idx')}: VN VAT Reporting Category"
            )
            continue
        value = d(line.get("reporting_value"))
        tax = line.get("tax_amount")
        tax_value = None if tax is None else d(tax)
        for key in ("value_indicator", "secondary_value_indicator"):
            indicator = category.get(key)
            if indicator:
                indicators[indicator] = indicators.get(indicator, Decimal("0")) + value
        for key in ("tax_indicator", "secondary_tax_indicator"):
            indicator = category.get(key)
            if indicator:
                if tax_value is None:
                    missing.append(
                        f"{line.get('doctype')} {line.get('parent')} row {line.get('idx')}: exact native VAT amount"
                    )
                else:
                    indicators[indicator] = indicators.get(indicator, Decimal("0")) + tax_value
        if category.get("requires_reduction_annex"):
            warnings.append(
                f"{line.get('doctype')} {line.get('parent')} row {line.get('idx')} requires the applicable temporary VAT-reduction annex."
            )
    return indicators, sorted(set(missing)), sorted(set(warnings))
