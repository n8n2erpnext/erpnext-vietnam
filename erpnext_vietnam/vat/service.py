from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal

import frappe
from frappe.utils import getdate

from erpnext_vietnam.accounting.roles import VAT_INPUT_ROLE, VAT_OUTPUT_ROLE
from erpnext_vietnam.accounting.service import resolve_coa_mapping
from erpnext_vietnam.declarations.vat_reporting import resolve_reporting_category
from erpnext_vietnam.legal.models import EffectiveRule, LegalReference
from erpnext_vietnam.vat.models import VATClassificationDefinition
from erpnext_vietnam.vat.resolver import VATClassificationError, resolve_vat

TEMP_REDUCTION_RULE_CODE = "VAT.TEMP_REDUCTION_RATE"


def _rate_rule_from_db(code: str, when: date):
    rows = frappe.get_all(
        "VN Rate Rule",
        filters={"code": code, "rule_status": "Released", "effective_from": ["<=", when]},
        fields=["name", "code", "decimal_value", "effective_from", "effective_to", "priority", "legal_instrument", "legal_reference_detail"],
        order_by="priority desc, effective_from desc",
    )
    rows = [r for r in rows if not r.effective_to or getdate(r.effective_to) >= when]
    if not rows:
        return None
    best = rows[0]
    tied = [r for r in rows if (r.priority, getdate(r.effective_from)) == (best.priority, getdate(best.effective_from))]
    if len(tied) > 1:
        frappe.throw(f"Ambiguous released VN Rate Rule {code} on {when}")
    refs = ()
    if best.legal_instrument:
        refs = (LegalReference(best.legal_instrument, best.legal_reference_detail),)
    return EffectiveRule(
        code=best.code,
        effective_from=getdate(best.effective_from),
        effective_to=getdate(best.effective_to) if best.effective_to else None,
        value=Decimal(str(best.decimal_value)),
        priority=int(best.priority or 100),
        status="Released",
        references=refs,
    )


def resolve_classification(classification_name: str, when: date):
    doc = frappe.get_doc("VN VAT Classification", classification_name)
    if doc.classification_status != "Released":
        raise VATClassificationError(f"VAT classification {classification_name} is not Released")
    definition = VATClassificationDefinition(
        code=doc.code,
        treatment=doc.treatment,
        statutory_rate=Decimal(str(doc.statutory_rate)),
        effective_from=getdate(doc.effective_from),
        effective_to=getdate(doc.effective_to) if doc.effective_to else None,
        temporary_reduction_eligible=bool(doc.temporary_reduction_eligible),
        rule_set=doc.rule_set,
        legal_instrument=doc.legal_instrument,
        legal_reference_detail=doc.legal_reference_detail,
    )
    temp_rule = _rate_rule_from_db(TEMP_REDUCTION_RULE_CODE, getdate(when)) if definition.temporary_reduction_eligible else None
    return resolve_vat(definition, getdate(when), temp_rule)


def _settings(company: str):
    name = frappe.db.get_value("VN Localization Settings", {"company": company}, "name")
    return frappe.get_doc("VN Localization Settings", name) if name else None


def _row_classification(row):
    if getattr(row, "vn_vat_classification", None):
        return row.vn_vat_classification
    if getattr(row, "item_code", None):
        return frappe.db.get_value("Item", row.item_code, "vn_vat_classification")
    return None


def _native_vat_rate(row, account: str | None):
    if not account or not getattr(row, "item_tax_rate", None):
        return None
    try:
        rates = json.loads(row.item_tax_rate) if isinstance(row.item_tax_rate, str) else row.item_tax_rate
    except Exception:
        return None
    if not isinstance(rates, dict) or account not in rates:
        return None
    return Decimal(str(rates[account]))


def validate_item(doc, method=None):
    classification = getattr(doc, "vn_vat_classification", None)
    if not classification:
        return
    status = frappe.db.get_value("VN VAT Classification", classification, "classification_status")
    if status == "Retired":
        frappe.throw(f"VN VAT Classification {classification} is retired")


def validate_invoice_vat(doc, method=None):
    settings = _settings(doc.company)
    if not settings or settings.vat_method == "NOT_CONFIGURED":
        return
    when = getdate(getattr(doc, "posting_date", None) or frappe.utils.today())
    role = VAT_OUTPUT_ROLE if doc.doctype == "Sales Invoice" else VAT_INPUT_ROLE
    mapping = resolve_coa_mapping(doc.company, role, when, settings.accounting_regime)
    vat_account = mapping.account if mapping else None
    strict = getattr(settings, "vat_validation_mode", "Advisory") == "Strict"
    snapshot_rows = []
    classified = 0

    for row in doc.items:
        classification = _row_classification(row)
        reporting_name = getattr(row, "vn_vat_reporting_category", None)
        direction = "Output" if doc.doctype == "Sales Invoice" else "Input"
        result = None

        if classification:
            classified += 1
            result = resolve_classification(classification, when)
            row.vn_vat_classification = classification
            row.vn_vat_treatment = result.treatment
            row.vn_vat_rate = float(result.rate)
            row.vn_vat_snapshot_hash = result.snapshot_hash
            native_rate = _native_vat_rate(row, vat_account)
            if native_rate is not None and native_rate != result.rate:
                frappe.throw(
                    f"Row {row.idx}: ERPNext Item Tax Template VAT rate {native_rate}% does not match "
                    f"VN classification {result.treatment} ({result.rate}%)"
                )
        elif hasattr(row, "vn_vat_snapshot_hash"):
            row.vn_vat_snapshot_hash = None

        reporting = None
        reporting_snapshot_hash = None
        if reporting_name:
            reporting = resolve_reporting_category(
                reporting_name, direction, when, result.treatment if result else None
            )
            reporting_snapshot_hash = reporting["snapshot_hash"]
            if hasattr(row, "vn_vat_reporting_snapshot_hash"):
                row.vn_vat_reporting_snapshot_hash = reporting_snapshot_hash
        elif hasattr(row, "vn_vat_reporting_snapshot_hash"):
            row.vn_vat_reporting_snapshot_hash = None

        if not classification and strict:
            # Reporting-only buckets [32a]/[32b]/[34a] are intentionally separate from VAT-rate treatment.
            reporting_only = reporting and reporting.get("treatment_constraint") == "ANY_REVIEW" and direction == "Output"
            if not reporting_only:
                frappe.throw(f"Row {row.idx}: VN VAT Classification is required in Strict mode")

        if doc.doctype == "Purchase Invoice":
            ratio = getattr(row, "vn_input_vat_deductible_ratio", None)
            if ratio not in (None, "") and not (0 <= float(ratio) <= 100):
                frappe.throw(f"Row {row.idx}: deductible input VAT ratio must be between 0 and 100")

        if classification or reporting_name:
            snapshot_rows.append({
                "idx": row.idx, "classification": classification,
                "snapshot_hash": result.snapshot_hash if result else None,
                "reporting_category": reporting_name, "reporting_snapshot_hash": reporting_snapshot_hash,
            })

    payload = json.dumps(snapshot_rows, sort_keys=True, separators=(",", ":"))
    if hasattr(doc, "vn_vat_snapshot_hash"):
        doc.vn_vat_snapshot_hash = hashlib.sha256(payload.encode()).hexdigest() if snapshot_rows else None
    if hasattr(doc, "vn_vat_validation_status"):
        doc.vn_vat_validation_status = "Validated" if classified else "Unclassified"


def validate_sales_invoice(doc, method=None):
    return validate_invoice_vat(doc, method)


def validate_purchase_invoice(doc, method=None):
    return validate_invoice_vat(doc, method)
