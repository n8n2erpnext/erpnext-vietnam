from __future__ import annotations

import json

import frappe

from erpnext_vietnam.integration.adapters.sandbox import sandbox_einvoice_adapter
from erpnext_vietnam.integration.orchestrator import prepare_submission, reconcile_submission, submit_submission

COUNT_DOCTYPES = (
    "GL Entry", "Journal Entry", "VN Localization Settings", "VN Integration Endpoint",
    "VN Submission", "VN Submission Attempt",
)


def _counts():
    return {doctype: frappe.db.count(doctype) for doctype in COUNT_DOCTYPES}


def _enable_gateway_in_transaction(company: str):
    existing = frappe.db.get_value("VN Localization Settings", {"company": company}, "name")
    if existing:
        doc = frappe.get_doc("VN Localization Settings", existing)
        doc.enable_compliance_gateway = 1
        doc.save(ignore_permissions=True)
        return doc
    profile = frappe.db.get_value("VN Business Profile", {}, "name", order_by="name asc")
    if not profile:
        frappe.throw("P4B UAT requires at least one seeded VN Business Profile")
    return frappe.get_doc({
        "doctype": "VN Localization Settings", "company": company, "business_profile": profile,
        "accounting_regime": "TT99_2025", "vat_method": "DEDUCTION", "vat_validation_mode": "Advisory",
        "enable_compliance_gateway": 1,
    }).insert(ignore_permissions=True)


def run_gateway_rollback_uat(company: str) -> dict:
    before = _counts()
    sandbox_einvoice_adapter.reset()
    result = {"company": company, "before_counts": before}
    try:
        _enable_gateway_in_transaction(company)
        endpoint = frappe.get_doc({
            "doctype": "VN Integration Endpoint", "endpoint_name": "P4B Rollback UAT",
            "company": company, "adapter": "sandbox.einvoice.v1", "channel": "E_INVOICE",
            "environment": "SANDBOX", "enabled": 1,
            "capabilities_json": json.dumps(["VALIDATE", "SUBMIT", "RECONCILE"]),
            "timeout_seconds": 5,
        }).insert(ignore_permissions=True)
        submission = prepare_submission(
            company=company, endpoint=endpoint.name, submission_type="E_INVOICE_UAT",
            schema_version="sandbox-v1", payload={"sandbox_outcome": "TIMEOUT", "uat": True},
        )
        key = submission.idempotency_key
        submission = submit_submission(submission.name)
        if submission.status != "UNKNOWN":
            frappe.throw("P4B UAT expected UNKNOWN after synthetic timeout")
        retry_blocked = False
        try:
            submit_submission(submission.name)
        except frappe.ValidationError:
            retry_blocked = True
        if not retry_blocked:
            frappe.throw("P4B UAT expected blind re-submit to be blocked")
        submission = reconcile_submission(submission.name)
        if submission.status != "ACCEPTED":
            frappe.throw("P4B UAT expected reconciliation to resolve ACCEPTED")
        attempts = frappe.get_all(
            "VN Submission Attempt", filters={"submission": submission.name},
            fields=["attempt_no", "operation", "outcome"], order_by="attempt_no asc",
        )
        if sandbox_einvoice_adapter.submit_calls.get(key) != 1:
            frappe.throw("P4B UAT detected duplicate provider submit call")
        result.update({
            "submission": submission.name, "status_after_reconcile": submission.status,
            "retry_blocked": retry_blocked, "provider_submit_calls": sandbox_einvoice_adapter.submit_calls.get(key),
            "attempts": attempts, "during_counts": _counts(),
        })
    finally:
        frappe.db.rollback()
        sandbox_einvoice_adapter.reset()
    result["after_counts"] = _counts()
    result["rollback_clean"] = result["after_counts"] == before
    return result
