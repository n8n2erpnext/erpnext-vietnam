from __future__ import annotations

import json

import frappe
from frappe.utils import now_datetime

from erpnext_vietnam.declarations.canonical import canonical_json, payload_hash
from erpnext_vietnam.einvoice.canonical import build_canonical_invoice, SCHEMA_VERSION
from erpnext_vietnam.einvoice.lifecycle import operation_idempotency_key
from erpnext_vietnam.accounting.roles import VAT_OUTPUT_ROLE
from erpnext_vietnam.accounting.service import resolve_coa_mapping


def _settings(company: str):
    name = frappe.db.get_value("VN Localization Settings", {"company": company}, "name")
    return frappe.get_doc("VN Localization Settings", name) if name else None


def _company_party(company: str) -> dict:
    row = frappe.db.get_value("Company", company, ["company_name", "tax_id"], as_dict=True) or {}
    return {"legal_name": row.get("company_name") or company, "tax_id": row.get("tax_id")}


def _buyer_party(doc) -> dict:
    tax_id = getattr(doc, "tax_id", None)
    if not tax_id and getattr(doc, "customer", None):
        tax_id = frappe.db.get_value("Customer", doc.customer, "tax_id")
    return {
        "legal_name": getattr(doc, "customer_name", None) or getattr(doc, "customer", None),
        "tax_id": tax_id,
        "address": getattr(doc, "address_display", None),
    }


def _native_vat_total(doc) -> tuple[float | None, list[str]]:
    mapping = resolve_coa_mapping(doc.company, VAT_OUTPUT_ROLE, doc.posting_date)
    if not mapping:
        return None, ["missing effective VAT_OUTPUT_PAYABLE account mapping"]
    vat_account = mapping.account
    total = 0.0
    review_rows = []
    matched = False
    for row in getattr(doc, "taxes", []) or []:
        amount = float(getattr(row, "tax_amount", 0) or 0)
        account = getattr(row, "account_head", None)
        if account == vat_account:
            total += amount
            matched = True
        elif amount:
            review_rows.append(getattr(row, "description", None) or account or str(row.idx))
    if not matched:
        return None, [f"no native Sales Taxes and Charges row mapped to {vat_account}"] + review_rows
    return total, review_rows


def canonical_source_from_sales_invoice(doc) -> dict:
    native_vat_total, tax_warnings = _native_vat_total(doc)
    return {
        "source": {"doctype": "Sales Invoice", "name": doc.name, "posting_date": doc.posting_date, "docstatus": doc.docstatus},
        "seller": {**_company_party(doc.company), "address": getattr(doc, "company_address_display", None)},
        "buyer": _buyer_party(doc),
        "invoice_type": "VAT_INVOICE",
        "currency": doc.currency,
        "exchange_rate": getattr(doc, "conversion_rate", 1),
        "currency_precision": doc.precision("grand_total") if hasattr(doc, "precision") else 2,
        "lines": [{
            "idx": row.idx, "item_code": row.item_code, "description": row.description, "qty": row.qty, "uom": row.uom,
            "net_amount": row.net_amount, "vat_classification": getattr(row, "vn_vat_classification", None),
            "vat_treatment": getattr(row, "vn_vat_treatment", None), "vat_rate": getattr(row, "vn_vat_rate", None),
            "vat_snapshot_hash": getattr(row, "vn_vat_snapshot_hash", None),
            "vat_reporting_category": getattr(row, "vn_vat_reporting_category", None),
        } for row in doc.items],
        "net_total": doc.net_total, "native_vat_total": native_vat_total, "grand_total": doc.grand_total,
        "native_tax_warnings": tax_warnings,
    }


def preview_einvoice(sales_invoice: str) -> dict:
    doc = frappe.get_doc("Sales Invoice", sales_invoice)
    if doc.docstatus != 1:
        frappe.throw("VN e-invoice preparation requires a submitted Sales Invoice")
    settings = _settings(doc.company)
    enabled = bool(settings and settings.enable_einvoice)
    source = canonical_source_from_sales_invoice(doc)
    payload = build_canonical_invoice(source)
    if source.get("native_tax_warnings"):
        payload["warnings"] = sorted(set(payload["warnings"] + ["Native tax rows require accountant review: " + ", ".join(source["native_tax_warnings"])]))
    return {
        "company": doc.company, "sales_invoice": doc.name, "feature_enabled": enabled,
        "schema_version": SCHEMA_VERSION, "canonical_payload": payload,
        "canonical_payload_hash": payload["payload_hash"], "ready": payload["ready"],
        "read_only": True, "external_transport": False,
    }


@frappe.whitelist()
def get_einvoice_preview(sales_invoice: str):
    if not frappe.has_permission("Sales Invoice", ptype="read"):
        frappe.throw("Not permitted to read Sales Invoice", frappe.PermissionError)
    return preview_einvoice(sales_invoice)


def prepare_companion(sales_invoice: str, *, require_feature_enabled: bool = True):
    source_doc = frappe.get_doc("Sales Invoice", sales_invoice)
    if require_feature_enabled:
        settings = _settings(source_doc.company)
        if not settings or not settings.enable_einvoice:
            return None
    preview = preview_einvoice(sales_invoice)
    existing = frappe.db.get_value("VN E-Invoice", {"sales_invoice": sales_invoice, "revision": 1}, "name")
    if existing:
        return frappe.get_doc("VN E-Invoice", existing)
    doc = frappe.get_doc({
        "doctype": "VN E-Invoice", "company": preview["company"], "sales_invoice": sales_invoice,
        "invoice_type": "VAT_INVOICE", "revision": 1, "status": "PREPARED" if preview["ready"] else "DRAFT",
        "schema_version": preview["schema_version"],
        "canonical_payload_json": canonical_json(preview["canonical_payload"]),
        "canonical_payload_hash": preview["canonical_payload_hash"],
        "issue_idempotency_key": operation_idempotency_key(preview["company"], sales_invoice, "ISSUE", 1),
        "prepared_at": now_datetime(),
    }).insert(ignore_permissions=True)
    return doc


@frappe.whitelist()
def create_einvoice_companion(sales_invoice: str):
    if not frappe.has_permission("VN E-Invoice", ptype="create"):
        frappe.throw("Not permitted to create VN E-Invoice", frappe.PermissionError)
    doc = prepare_companion(sales_invoice, require_feature_enabled=False)
    return doc.as_dict() if doc else None
