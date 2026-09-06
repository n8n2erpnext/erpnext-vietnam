from __future__ import annotations

import json

import frappe

from erpnext_vietnam.declarations.canonical import canonical_json, payload_hash
from erpnext_vietnam.einvoice.gateway import queue_einvoice, reconcile_einvoice, submit_einvoice
from erpnext_vietnam.einvoice.lifecycle import operation_idempotency_key
from erpnext_vietnam.integration.adapters.sandbox import sandbox_einvoice_adapter

COUNT_DOCTYPES = (
    "GL Entry", "Journal Entry", "VN Localization Settings", "VN Integration Endpoint",
    "VN E-Invoice Profile", "VN E-Invoice", "VN Submission", "VN Submission Attempt",
)


def _counts():
    return {doctype: frappe.db.count(doctype) for doctype in COUNT_DOCTYPES}


def _settings(company: str):
    existing = frappe.db.get_value("VN Localization Settings", {"company": company}, "name")
    if existing:
        doc = frappe.get_doc("VN Localization Settings", existing)
        doc.enable_compliance_gateway = 1
        doc.save(ignore_permissions=True)
        return doc
    business_profile = frappe.db.get_value("VN Business Profile", {}, "name", order_by="name asc")
    return frappe.get_doc({
        "doctype": "VN Localization Settings", "company": company, "business_profile": business_profile,
        "accounting_regime": "TT99_2025", "vat_method": "DEDUCTION", "vat_validation_mode": "Advisory",
        "enable_compliance_gateway": 1,
    }).insert(ignore_permissions=True)


def run_einvoice_bridge_rollback_uat(sales_invoice: str) -> dict:
    invoice = frappe.get_doc("Sales Invoice", sales_invoice)
    if invoice.docstatus != 1:
        frappe.throw("P4C UAT requires a submitted Sales Invoice")
    company = invoice.company
    before = _counts()
    sandbox_einvoice_adapter.reset()
    result = {"sales_invoice": sales_invoice, "company": company, "before_counts": before}
    try:
        _settings(company)
        endpoint = frappe.get_doc({
            "doctype": "VN Integration Endpoint", "endpoint_name": "P4C E-Invoice Rollback UAT",
            "company": company, "adapter": "sandbox.einvoice.v1", "channel": "E_INVOICE",
            "environment": "SANDBOX", "enabled": 1,
            "capabilities_json": json.dumps(["VALIDATE", "SUBMIT", "RECONCILE"]), "timeout_seconds": 5,
        }).insert(ignore_permissions=True)
        profile = frappe.get_doc({
            "doctype": "VN E-Invoice Profile", "profile_name": "P4C Sandbox Profile", "company": company,
            "enabled": 1, "endpoint": endpoint.name, "invoice_type": "VAT_INVOICE",
            "canonical_schema_version": "VN-EINVOICE-CANONICAL-2026-01", "signing_mode": "UNSPECIFIED",
        }).insert(ignore_permissions=True)
        base_payload = {
            "schema": "VN-EINVOICE-CANONICAL-2026-01", "ready": True,
            "source": {"doctype": "Sales Invoice", "name": invoice.name, "docstatus": invoice.docstatus},
            "seller": {"legal_name": company, "tax_id": "UAT"},
            "buyer": {"legal_name": "UAT Buyer", "tax_id": "UAT"},
            "lines": [], "net_total": 0, "vat_total": 0, "grand_total": 0,
            "missing_required": [], "warnings": [], "sandbox_outcome": "TIMEOUT",
        }
        base_payload["payload_hash"] = payload_hash(base_payload)
        revision = int(frappe.db.get_value("VN E-Invoice", {"sales_invoice": invoice.name}, "revision", order_by="revision desc") or 0) + 1000
        einvoice = frappe.get_doc({
            "doctype": "VN E-Invoice", "company": company, "sales_invoice": invoice.name,
            "profile": profile.name, "invoice_type": "VAT_INVOICE", "revision": revision,
            "status": "PREPARED", "schema_version": "VN-EINVOICE-CANONICAL-2026-01",
            "canonical_payload_json": canonical_json(base_payload),
            "issue_idempotency_key": operation_idempotency_key(company, invoice.name, "ISSUE", revision),
        }).insert(ignore_permissions=True)
        einvoice, submission = queue_einvoice(einvoice.name)
        if einvoice.status != "QUEUED" or submission.status != "READY":
            frappe.throw("P4C UAT failed to queue e-invoice into READY submission")
        einvoice, submission = submit_einvoice(einvoice.name)
        if einvoice.status != "UNKNOWN" or submission.status != "UNKNOWN":
            frappe.throw("P4C UAT expected synthetic timeout to yield UNKNOWN")
        retry_blocked = False
        try:
            submit_einvoice(einvoice.name)
        except frappe.ValidationError:
            retry_blocked = True
        if not retry_blocked:
            frappe.throw("P4C UAT expected blind e-invoice retry to be blocked")
        einvoice, submission = reconcile_einvoice(einvoice.name)
        if einvoice.status != "ACCEPTED" or submission.status != "ACCEPTED":
            frappe.throw("P4C UAT reconciliation did not resolve ACCEPTED")
        calls = sandbox_einvoice_adapter.submit_calls.get(submission.idempotency_key)
        if calls != 1:
            frappe.throw("P4C UAT detected duplicate provider submit call")
        result.update({
            "einvoice": einvoice.name, "submission": submission.name, "final_status": einvoice.status,
            "retry_blocked": retry_blocked, "provider_submit_calls": calls,
            "attempts": frappe.get_all("VN Submission Attempt", filters={"submission": submission.name},
                fields=["attempt_no", "operation", "outcome"], order_by="attempt_no asc"),
            "during_counts": _counts(),
        })
    finally:
        frappe.db.rollback()
        sandbox_einvoice_adapter.reset()
    result["after_counts"] = _counts()
    result["rollback_clean"] = result["after_counts"] == before
    return result
