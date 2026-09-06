from __future__ import annotations

from collections import Counter
from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import getdate

from erpnext_vietnam.accounting.roles import (
    VAT_INPUT_ROLE,
    VAT_OUTPUT_ROLE,
    validate_statutory_role,
)
from erpnext_vietnam.vat.reconciliation_math import period_is_covered, summarize_vat_gl

VAT_INPUT_FIXED_ASSET_ROLE = "VAT_INPUT_DEDUCTIBLE_FIXED_ASSETS"


def _settings(company: str):
    name = frappe.db.get_value("VN Localization Settings", {"company": company}, "name")
    return frappe.get_doc("VN Localization Settings", name) if name else None


def _overlapping_mappings(company: str, role: str, regime: str, from_date, to_date):
    validate_statutory_role(role)
    rows = frappe.get_all(
        "VN COA Mapping",
        filters={
            "company": company,
            "statutory_role": role,
            "accounting_regime": regime,
            "effective_from": ["<=", to_date],
        },
        fields=["name", "account", "statutory_role", "statutory_code", "effective_from", "effective_to", "rule_set"],
        order_by="effective_from asc",
    )
    return [r for r in rows if not r.effective_to or getdate(r.effective_to) >= getdate(from_date)]


def _query_gl(company: str, from_date, to_date, accounts: set[str]):
    if not accounts:
        return []
    return frappe.get_all(
        "GL Entry",
        filters={
            "company": company,
            "posting_date": ["between", [from_date, to_date]],
            "is_cancelled": 0,
            "account": ["in", sorted(accounts)],
        },
        fields=["posting_date", "account", "debit", "credit", "voucher_type", "voucher_no"],
        order_by="posting_date asc, creation asc",
        limit_page_length=0,
    )


def _invoice_summary(doctype: str, from_date, to_date, company: str) -> dict:
    rows = frappe.get_all(
        doctype,
        filters={"company": company, "docstatus": 1, "posting_date": ["between", [from_date, to_date]]},
        fields=["name", "vn_vat_validation_status", "vn_vat_snapshot_hash"],
        limit_page_length=0,
    )
    statuses = Counter((r.vn_vat_validation_status or "Missing") for r in rows)
    return {
        "total_submitted": len(rows),
        "status_counts": dict(sorted(statuses.items())),
        "with_snapshot": sum(1 for r in rows if r.vn_vat_snapshot_hash),
        "names": {r.name: bool(r.vn_vat_snapshot_hash) for r in rows},
    }


def _item_coverage(parent_doctype: str, child_table: str, from_date, to_date, company: str) -> dict:
    rows = frappe.db.sql(
        f"""
        select child.vn_vat_treatment, child.vn_vat_snapshot_hash
        from `tab{child_table}` child
        inner join `tab{parent_doctype}` parent on parent.name = child.parent
        where parent.company = %(company)s and parent.docstatus = 1
          and parent.posting_date between %(from_date)s and %(to_date)s
        """,
        {"company": company, "from_date": from_date, "to_date": to_date},
        as_dict=True,
    )
    treatments = Counter((r.vn_vat_treatment or "UNCLASSIFIED") for r in rows)
    return {
        "total_rows": len(rows),
        "classified_rows": sum(1 for r in rows if r.vn_vat_treatment and r.vn_vat_snapshot_hash),
        "treatment_counts": dict(sorted(treatments.items())),
    }


def _purchase_evidence(from_date, to_date, company: str) -> dict:
    rows = frappe.db.sql(
        """
        select child.vn_input_vat_deduction_status as status,
               child.vn_input_vat_deductible_ratio as ratio,
               child.vn_input_vat_evidence_reference as evidence
        from `tabPurchase Invoice Item` child
        inner join `tabPurchase Invoice` parent on parent.name = child.parent
        where parent.company = %(company)s and parent.docstatus = 1
          and parent.posting_date between %(from_date)s and %(to_date)s
          and child.vn_vat_treatment not in ('NON_TAXABLE', 'ZERO_RATE_0')
        """,
        {"company": company, "from_date": from_date, "to_date": to_date},
        as_dict=True,
    )
    statuses = Counter((r.status or "Unknown") for r in rows)
    return {
        "taxable_input_rows": len(rows),
        "status_counts": dict(sorted(statuses.items())),
        "with_evidence_reference": sum(1 for r in rows if r.evidence),
        "ratio_review_required": sum(1 for r in rows if r.ratio is None or float(r.ratio) < 100),
    }


def _voucher_snapshot_coverage(gl_entries: list[dict], sales: dict, purchases: dict) -> dict:
    invoice_vouchers = set()
    with_snapshot = set()
    correction_entries = 0
    for row in gl_entries:
        voucher_type = row.get("voucher_type")
        voucher_no = row.get("voucher_no")
        if voucher_type == "Sales Invoice" and voucher_no:
            invoice_vouchers.add((voucher_type, voucher_no))
            if sales["names"].get(voucher_no):
                with_snapshot.add((voucher_type, voucher_no))
        elif voucher_type == "Purchase Invoice" and voucher_no:
            invoice_vouchers.add((voucher_type, voucher_no))
            if purchases["names"].get(voucher_no):
                with_snapshot.add((voucher_type, voucher_no))
        else:
            correction_entries += 1
    return {
        "invoice_vouchers": len(invoice_vouchers),
        "invoice_vouchers_with_snapshot": len(with_snapshot),
        "non_invoice_or_correction_gl_entries": correction_entries,
    }


def _decimal_json(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01")))


def _mapping_payload(rows):
    return [
        {
            "name": r.name,
            "account": r.account,
            "statutory_role": r.statutory_role,
            "statutory_code": r.statutory_code,
            "effective_from": str(r.effective_from),
            "effective_to": str(r.effective_to) if r.effective_to else None,
            "rule_set": r.rule_set,
        }
        for r in rows
    ]


def build_vat_reconciliation(company: str, from_date, to_date) -> dict:
    if not company or not frappe.db.exists("Company", company):
        frappe.throw(_("A valid Company is required."))
    from_date, to_date = getdate(from_date), getdate(to_date)
    if from_date > to_date:
        frappe.throw(_("From Date cannot be after To Date."))

    settings = _settings(company)
    warnings = []
    if not settings:
        return {"company": company, "from_date": str(from_date), "to_date": str(to_date), "configured": False,
                "warnings": ["VN Localization Settings is not configured for this Company."]}
    if settings.vat_method == "NOT_CONFIGURED":
        warnings.append("VAT Method is NOT_CONFIGURED; reconciliation is accounting-only until VAT setup is completed.")

    regime = settings.accounting_regime
    output_mappings = _overlapping_mappings(company, VAT_OUTPUT_ROLE, regime, from_date, to_date)
    input_goods = _overlapping_mappings(company, VAT_INPUT_ROLE, regime, from_date, to_date)
    input_fixed = _overlapping_mappings(company, VAT_INPUT_FIXED_ASSET_ROLE, regime, from_date, to_date)
    input_mappings = input_goods + input_fixed

    if not period_is_covered(output_mappings, from_date, to_date):
        warnings.append("VAT output mapping does not cover the full requested period.")
    if not period_is_covered(input_goods, from_date, to_date):
        warnings.append("VAT deductible input goods/services mapping does not cover the full requested period.")

    all_accounts = {r.account for r in output_mappings + input_mappings if r.account}
    gl_entries = _query_gl(company, from_date, to_date, all_accounts)
    gl = summarize_vat_gl(gl_entries, _mapping_payload(output_mappings), _mapping_payload(input_mappings))
    if gl["ambiguous_entries"]:
        warnings.append(f"{gl['ambiguous_entries']} GL entries match both active input and output VAT mappings and were excluded.")

    sales = _invoice_summary("Sales Invoice", from_date, to_date, company)
    purchases = _invoice_summary("Purchase Invoice", from_date, to_date, company)
    sales_items = _item_coverage("Sales Invoice", "Sales Invoice Item", from_date, to_date, company)
    purchase_items = _item_coverage("Purchase Invoice", "Purchase Invoice Item", from_date, to_date, company)
    purchase_evidence = _purchase_evidence(from_date, to_date, company)
    voucher_coverage = _voucher_snapshot_coverage(gl_entries, sales, purchases)
    sales.pop("names", None)
    purchases.pop("names", None)

    for key in ("output_vat_gl_movement", "input_vat_gl_movement", "net_vat_accounting_movement"):
        gl[key] = _decimal_json(gl[key])

    return {
        "company": company,
        "from_date": str(from_date),
        "to_date": str(to_date),
        "configured": True,
        "accounting_regime": regime,
        "vat_method": settings.vat_method,
        "mappings": {"output": _mapping_payload(output_mappings), "input": _mapping_payload(input_mappings)},
        "gl": gl,
        "invoice_coverage": {"sales": sales, "purchases": purchases, "sales_items": sales_items, "purchase_items": purchase_items},
        "purchase_input_evidence": purchase_evidence,
        "gl_voucher_snapshot_coverage": voucher_coverage,
        "warnings": warnings,
        "scope_note": "Pre-declaration accounting reconciliation only. No statutory declaration is created or submitted.",
    }


@frappe.whitelist()
def get_vat_reconciliation(company: str, from_date, to_date):
    if not frappe.has_permission("GL Entry", ptype="read"):
        frappe.throw(_("Not permitted to read accounting entries."), frappe.PermissionError)
    return build_vat_reconciliation(company, from_date, to_date)
