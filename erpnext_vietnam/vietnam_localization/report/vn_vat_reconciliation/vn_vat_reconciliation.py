from __future__ import annotations

import frappe
from frappe import _

from erpnext_vietnam.vat.reconciliation import build_vat_reconciliation


def _coverage(done: int, total: int) -> float:
    return round((done / total) * 100, 2) if total else 100.0


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.company or not filters.from_date or not filters.to_date:
        frappe.throw(_("Company, From Date and To Date are required."))
    result = build_vat_reconciliation(filters.company, filters.from_date, filters.to_date)
    currency = frappe.db.get_value("Company", filters.company, "default_currency")
    gl = result.get("gl", {})
    coverage = result.get("invoice_coverage", {})
    sales = coverage.get("sales", {})
    purchases = coverage.get("purchases", {})
    sales_items = coverage.get("sales_items", {})
    purchase_items = coverage.get("purchase_items", {})
    evidence = result.get("purchase_input_evidence", {})

    rows = [
        {"metric": _("Output VAT GL movement"), "amount": gl.get("output_vat_gl_movement"), "status": "Accounting"},
        {"metric": _("Input VAT GL movement"), "amount": gl.get("input_vat_gl_movement"), "status": "Accounting"},
        {"metric": _("Net VAT accounting movement"), "amount": gl.get("net_vat_accounting_movement"), "status": "Accounting"},
        {"metric": _("Sales invoices with VAT snapshot"), "count": sales.get("with_snapshot", 0), "coverage": _coverage(sales.get("with_snapshot", 0), sales.get("total_submitted", 0)), "status": "Evidence"},
        {"metric": _("Purchase invoices with VAT snapshot"), "count": purchases.get("with_snapshot", 0), "coverage": _coverage(purchases.get("with_snapshot", 0), purchases.get("total_submitted", 0)), "status": "Evidence"},
        {"metric": _("Classified sales rows"), "count": sales_items.get("classified_rows", 0), "coverage": _coverage(sales_items.get("classified_rows", 0), sales_items.get("total_rows", 0)), "status": "Evidence"},
        {"metric": _("Classified purchase rows"), "count": purchase_items.get("classified_rows", 0), "coverage": _coverage(purchase_items.get("classified_rows", 0), purchase_items.get("total_rows", 0)), "status": "Evidence"},
        {"metric": _("Taxable input rows with evidence reference"), "count": evidence.get("with_evidence_reference", 0), "coverage": _coverage(evidence.get("with_evidence_reference", 0), evidence.get("taxable_input_rows", 0)), "status": "Evidence"},
        {"metric": _("Warnings"), "count": len(result.get("warnings", [])), "status": "Review" if result.get("warnings") else "OK", "detail": " | ".join(result.get("warnings", []))},
    ]
    columns = [
        {"label": _("Metric"), "fieldname": "metric", "fieldtype": "Data", "width": 300},
        {"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "options": "currency", "width": 160},
        {"label": _("Count"), "fieldname": "count", "fieldtype": "Int", "width": 100},
        {"label": _("Coverage %"), "fieldname": "coverage", "fieldtype": "Percent", "width": 120},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 120},
        {"label": _("Detail"), "fieldname": "detail", "fieldtype": "Data", "width": 420},
        {"label": _("Currency"), "fieldname": "currency", "fieldtype": "Data", "hidden": 1},
    ]
    for row in rows:
        row["currency"] = currency
    summary = [
        {"value": gl.get("output_vat_gl_movement", 0), "indicator": "Blue", "label": _("Output VAT movement"), "datatype": "Currency", "currency": currency},
        {"value": gl.get("input_vat_gl_movement", 0), "indicator": "Blue", "label": _("Input VAT movement"), "datatype": "Currency", "currency": currency},
        {"value": gl.get("net_vat_accounting_movement", 0), "indicator": "Orange" if result.get("warnings") else "Green", "label": _("Net VAT accounting movement"), "datatype": "Currency", "currency": currency},
    ]
    message = result.get("scope_note")
    return columns, rows, message, None, summary
