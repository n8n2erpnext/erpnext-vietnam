from __future__ import annotations

import json

import frappe
from frappe.utils import now_datetime

from erpnext_vietnam.declarations.canonical import canonical_json, payload_hash
from erpnext_vietnam.integration.evidence import evidence_snapshot_hash
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


def _latest_provider_request_id(submission_name: str) -> str | None:
    rows = frappe.get_all(
        "VN Submission Attempt", filters={"submission": submission_name},
        fields=["attempt_no", "request_id"], order_by="attempt_no desc", limit_page_length=10,
    )
    return next((row.request_id for row in rows if row.request_id), None)


def _apply_acceptance_archive(einvoice, submission) -> None:
    if not submission.acceptance_evidence_json:
        return
    try:
        evidence = json.loads(submission.acceptance_evidence_json)
    except json.JSONDecodeError:
        frappe.throw("Stored acceptance evidence is invalid JSON")
    if evidence_snapshot_hash(evidence) != submission.acceptance_evidence_hash:
        frappe.throw("Stored acceptance evidence hash does not match content")
    artifacts = {str(item.get("role") or "").upper(): item for item in evidence.get("artifacts", [])}
    final_xml = artifacts.get("FINAL_XML")
    rendering = artifacts.get("RENDERING")
    einvoice.provider_invoice_id = evidence.get("provider_document_id")
    einvoice.tax_authority_code = evidence.get("authority_code")
    einvoice.signing_certificate_serial = evidence.get("signing_certificate_serial")
    einvoice.issued_at = evidence.get("issued_at")
    einvoice.accepted_at = evidence.get("accepted_at")
    if final_xml:
        einvoice.final_xml_file = final_xml.get("file_url")
        einvoice.final_xml_sha256 = final_xml.get("sha256")
    if rendering:
        einvoice.rendering_file = rendering.get("file_url")
    einvoice.provider_response_json = canonical_json(evidence)
    archive = {
        "schema": "VN-EINVOICE-ARCHIVE-2026-01",
        "company": einvoice.company, "einvoice": einvoice.name, "sales_invoice": einvoice.sales_invoice,
        "revision": int(einvoice.revision), "canonical_payload_hash": einvoice.canonical_payload_hash,
        "issue_idempotency_key": einvoice.issue_idempotency_key, "submission": submission.name,
        "submission_payload_hash": submission.payload_hash, "submission_idempotency_key": submission.idempotency_key,
        "acceptance_evidence_hash": submission.acceptance_evidence_hash, "evidence": evidence,
    }
    einvoice.archive_snapshot_json = canonical_json(archive)
    einvoice.archive_snapshot_hash = payload_hash(archive)
    einvoice.archive_locked_at = submission.acceptance_recorded_at or now_datetime()


def _mirror_submission(einvoice, submission):
    einvoice.status = submission.status
    request_id = _latest_provider_request_id(submission.name)
    if request_id:
        einvoice.provider_request_id = request_id
    if submission.status == "ACCEPTED":
        _apply_acceptance_archive(einvoice, submission)
    einvoice.save(ignore_permissions=True)
    return einvoice


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
    einvoice = _mirror_submission(einvoice, submission)
    return einvoice, submission


def reconcile_einvoice(name: str):
    einvoice = frappe.get_doc("VN E-Invoice", name)
    if einvoice.status not in {"UNKNOWN", "SUBMITTING"}:
        frappe.throw("Only UNKNOWN or SUBMITTING e-invoices require reconciliation")
    submission = _submission_for(einvoice)
    if not submission:
        frappe.throw("E-invoice has no VN Submission to reconcile")
    submission = reconcile_submission(submission.name)
    einvoice = _mirror_submission(einvoice, submission)
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
