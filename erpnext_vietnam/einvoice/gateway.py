from __future__ import annotations

import json

import frappe

from erpnext_vietnam.declarations.canonical import payload_hash
from erpnext_vietnam.integration.orchestrator import prepare_submission, reconcile_submission, submit_submission

SUBMISSION_TYPE = "E_INVOICE_ISSUE"


def _load_ready_payload(einvoice):
    try:
        payload = json.loads(einvoice.canonical_payload_json or "{}")
    except json.JSONDecodeError:
        frappe.throw("Stored e-invoice canonical payload is invalid JSON")
    embedded = payload.pop("payload_hash", None)
    current = payload_hash(payload)
    if embedded and embedded != current:
        frappe.throw("Stored e-invoice canonical payload hash does not match content")
    if einvoice.canonical_payload_hash and einvoice.canonical_payload_hash != current:
        frappe.throw("Stored e-invoice canonical payload hash field does not match content")
    payload["payload_hash"] = current
    if payload.get("ready") is not True:
        frappe.throw("E-invoice canonical payload must be Ready before queueing")
    return payload


def _resolve_profile(einvoice):
    if einvoice.profile:
        profile = frappe.get_doc("VN E-Invoice Profile", einvoice.profile)
        if profile.company != einvoice.company:
            frappe.throw("E-invoice profile belongs to a different Company")
        if not profile.enabled:
            frappe.throw("E-invoice profile is disabled")
        return profile
    profiles = frappe.get_all(
        "VN E-Invoice Profile", filters={"company": einvoice.company, "enabled": 1},
        fields=["name"], order_by="name asc", limit_page_length=2,
    )
    if len(profiles) != 1:
        frappe.throw("Exactly one enabled VN E-Invoice Profile is required when the e-invoice has no explicit profile")
    return frappe.get_doc("VN E-Invoice Profile", profiles[0].name)


def _submission_for(einvoice):
    name = frappe.db.get_value(
        "VN Submission",
        {"source_doctype": "VN E-Invoice", "source_name": einvoice.name, "submission_type": SUBMISSION_TYPE,
         "status": ["!=", "CANCELLED"]},
        "name", order_by="creation desc",
    )
    return frappe.get_doc("VN Submission", name) if name else None


def queue_einvoice(name: str):
    einvoice = frappe.get_doc("VN E-Invoice", name)
    if einvoice.status not in {"PREPARED", "QUEUED"}:
        frappe.throw("Only PREPARED e-invoices may be queued")
    existing = _submission_for(einvoice)
    if existing:
        if einvoice.status == "PREPARED":
            einvoice.status = "QUEUED"
            einvoice.save(ignore_permissions=True)
        return einvoice, existing
    payload = _load_ready_payload(einvoice)
    profile = _resolve_profile(einvoice)
    submission = prepare_submission(
        company=einvoice.company,
        endpoint=profile.endpoint,
        submission_type=SUBMISSION_TYPE,
        schema_version=einvoice.schema_version,
        payload=payload,
        source_doctype="VN E-Invoice",
        source_name=einvoice.name,
        rule_snapshot_hash=einvoice.canonical_payload_hash,
    )
    einvoice.profile = profile.name
    einvoice.status = "QUEUED"
    einvoice.save(ignore_permissions=True)
    return einvoice, submission


def submit_einvoice(name: str):
    einvoice = frappe.get_doc("VN E-Invoice", name)
    if einvoice.status != "QUEUED":
        frappe.throw("Only QUEUED e-invoices may be submitted")
    submission = _submission_for(einvoice)
    if not submission:
        frappe.throw("Queued e-invoice has no VN Submission")
    einvoice.status = "SUBMITTING"
    einvoice.save(ignore_permissions=True)
    try:
        submission = submit_submission(submission.name)
    except Exception:
        einvoice.status = "QUEUED"
        einvoice.save(ignore_permissions=True)
        raise
    einvoice.status = submission.status
    if submission.external_reference:
        einvoice.provider_request_id = submission.external_reference
    einvoice.save(ignore_permissions=True)
    return einvoice, submission


def reconcile_einvoice(name: str):
    einvoice = frappe.get_doc("VN E-Invoice", name)
    if einvoice.status not in {"UNKNOWN", "SUBMITTING"}:
        frappe.throw("Only UNKNOWN or SUBMITTING e-invoices require reconciliation")
    submission = _submission_for(einvoice)
    if not submission:
        frappe.throw("E-invoice has no VN Submission to reconcile")
    submission = reconcile_submission(submission.name)
    einvoice.status = submission.status
    if submission.external_reference:
        einvoice.provider_request_id = submission.external_reference
    einvoice.save(ignore_permissions=True)
    return einvoice, submission


def _check_write(name: str):
    if not frappe.has_permission("VN E-Invoice", ptype="write", doc=name):
        frappe.throw("Not permitted to update VN E-Invoice", frappe.PermissionError)


@frappe.whitelist()
def queue(name: str):
    _check_write(name)
    einvoice, submission = queue_einvoice(name)
    return {"einvoice": einvoice.as_dict(), "submission": submission.as_dict()}


@frappe.whitelist()
def submit(name: str):
    _check_write(name)
    einvoice, submission = submit_einvoice(name)
    return {"einvoice": einvoice.as_dict(), "submission": submission.as_dict()}


@frappe.whitelist()
def reconcile(name: str):
    _check_write(name)
    einvoice, submission = reconcile_einvoice(name)
    return {"einvoice": einvoice.as_dict(), "submission": submission.as_dict()}
