from __future__ import annotations

import json
from typing import Any

import frappe
from frappe.utils import now_datetime

from erpnext_vietnam.declarations.canonical import canonical_json, payload_hash
from erpnext_vietnam.integration.builtin import register_builtin_adapters
from erpnext_vietnam.integration.certification import certification_hash
from erpnext_vietnam.integration.contracts import AmbiguousTransportError, SubmissionEnvelope, SubmissionResult
from erpnext_vietnam.integration.evidence import build_acceptance_snapshot, evidence_snapshot_hash, validate_acceptance_evidence
from erpnext_vietnam.integration.registry import get_adapter, require_production_certification

register_builtin_adapters()


def _gateway_enabled(company: str) -> bool:
    return bool(frappe.db.get_value("VN Localization Settings", {"company": company}, "enable_compliance_gateway"))


def _parse_json(value, label: str, default):
    if value in (None, ""):
        return default
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            frappe.throw(f"{label} must be valid JSON")
    return value


def _configured_capabilities(endpoint) -> set[str]:
    raw = _parse_json(endpoint.capabilities_json, "Endpoint capabilities", [])
    if isinstance(raw, dict):
        return {str(k).upper() for k, v in raw.items() if v}
    if isinstance(raw, list):
        return {str(v).upper() for v in raw}
    frappe.throw("Endpoint capabilities must be an array or object")


def _load_endpoint(endpoint_name: str, company: str, operation: str):
    endpoint = frappe.get_doc("VN Integration Endpoint", endpoint_name)
    if endpoint.company != company:
        frappe.throw("Integration Endpoint belongs to a different Company")
    if not endpoint.enabled:
        frappe.throw("Integration Endpoint is disabled")
    if not _gateway_enabled(company):
        frappe.throw("VN Compliance Gateway is disabled for this Company")
    try:
        adapter = get_adapter(endpoint.adapter)
    except ValueError as exc:
        frappe.throw(str(exc))
    if endpoint.channel != adapter.channel:
        frappe.throw("Integration Endpoint channel does not match adapter channel")
    operation = operation.upper()
    adapter_caps = {str(v).upper() for v in adapter.capabilities}
    if operation not in adapter_caps:
        frappe.throw(f"Adapter does not support {operation}")
    configured = _configured_capabilities(endpoint)
    if configured and operation not in configured:
        frappe.throw(f"Endpoint does not enable {operation}")
    if endpoint.environment == "PRODUCTION" and endpoint.adapter.startswith("sandbox."):
        frappe.throw("Sandbox adapters cannot be used by a PRODUCTION endpoint")
    if endpoint.environment == "PRODUCTION":
        try:
            certification = require_production_certification(endpoint.adapter, endpoint.channel)
        except ValueError as exc:
            frappe.throw(str(exc))
        current_hash = certification_hash(certification)
        if endpoint.adapter_certification_version != certification.certification_version or endpoint.adapter_certification_hash != current_hash:
            frappe.throw("Production endpoint adapter certification pin is missing or stale; review and save the endpoint")
    return endpoint, adapter


def _envelope(submission) -> SubmissionEnvelope:
    payload = _parse_json(submission.payload_json, "Submission payload", {})
    if not isinstance(payload, dict):
        frappe.throw("Submission payload must be a JSON object")
    return SubmissionEnvelope(
        submission_type=submission.submission_type,
        company=submission.company,
        schema_version=submission.schema_version,
        idempotency_key=submission.idempotency_key,
        payload_sha256=submission.payload_hash,
        payload=payload,
    )


def _request_hash(envelope: SubmissionEnvelope, operation: str) -> str:
    return payload_hash({
        "operation": operation,
        "submission_type": envelope.submission_type,
        "company": envelope.company,
        "schema_version": envelope.schema_version,
        "idempotency_key": envelope.idempotency_key,
        "payload_sha256": envelope.payload_sha256,
    })


def _next_attempt(submission_name: str, operation: str, envelope: SubmissionEnvelope):
    last = frappe.db.get_value(
        "VN Submission Attempt", {"submission": submission_name}, "attempt_no", order_by="attempt_no desc"
    ) or 0
    return frappe.get_doc({
        "doctype": "VN Submission Attempt",
        "submission": submission_name,
        "attempt_no": int(last) + 1,
        "operation": operation,
        "outcome": "PENDING",
        "started_at": now_datetime(),
        "request_hash": _request_hash(envelope, operation),
    }).insert(ignore_permissions=True)


def _finish_attempt(attempt, outcome: str, result: SubmissionResult | None = None, error: Exception | None = None):
    values: dict[str, Any] = {"outcome": outcome, "completed_at": now_datetime()}
    if result:
        acknowledgement = result.acknowledgement or {}
        values.update({
            "request_id": result.request_id,
            "response_id": result.response_id,
            "http_status": result.http_status,
            "response_hash": payload_hash(acknowledgement) if acknowledgement else None,
            "response_excerpt": canonical_json(acknowledgement)[:1000] if acknowledgement else None,
        })
    if error:
        values.update({"error_code": error.__class__.__name__, "error_message": str(error)[:1000]})
    for key, value in values.items():
        setattr(attempt, key, value)
    attempt.save(ignore_permissions=True)
    return attempt


def prepare_submission(*, company: str, endpoint: str, submission_type: str, schema_version: str,
                       payload: dict | str, source_doctype: str | None = None, source_name: str | None = None,
                       rule_set: str | None = None, rule_snapshot_hash: str | None = None):
    endpoint_doc, adapter = _load_endpoint(endpoint, company, "VALIDATE")
    payload = _parse_json(payload, "Canonical payload", {})
    if not isinstance(payload, dict):
        frappe.throw("Canonical payload must be a JSON object")
    doc = frappe.get_doc({
        "doctype": "VN Submission", "company": company, "submission_type": submission_type,
        "endpoint": endpoint_doc.name, "status": "DRAFT", "source_doctype": source_doctype,
        "source_name": source_name, "rule_set": rule_set, "rule_snapshot_hash": rule_snapshot_hash,
        "schema_version": schema_version, "payload_json": canonical_json(payload),
    })
    doc.insert(ignore_permissions=True)
    envelope = _envelope(doc)
    attempt = _next_attempt(doc.name, "VALIDATE", envelope)
    try:
        adapter.validate(envelope)
    except Exception as exc:
        _finish_attempt(attempt, "FAILED", error=exc)
        raise
    _finish_attempt(attempt, "SUCCESS", SubmissionResult(status="READY", acknowledgement={"validated": True}))
    doc.status = "READY"
    doc.save(ignore_permissions=True)
    return doc


def _persist_acceptance_evidence(submission, result: SubmissionResult) -> None:
    evidence = result.evidence
    if not evidence:
        return
    from frappe.utils.file_manager import save_file

    validate_acceptance_evidence(evidence)
    file_urls: dict[str, str] = {}
    for artifact in evidence.artifacts:
        file_doc = save_file(
            artifact.filename, bytes(artifact.content), "VN Submission", submission.name,
            is_private=1,
        )
        file_urls[artifact.role.upper()] = file_doc.file_url
    snapshot = build_acceptance_snapshot(evidence, file_urls=file_urls)
    snapshot_json = canonical_json(snapshot)
    snapshot_hash = evidence_snapshot_hash(snapshot)
    if submission.acceptance_evidence_hash and submission.acceptance_evidence_hash != snapshot_hash:
        frappe.throw("Accepted-provider evidence cannot be replaced by a different snapshot")
    submission.acceptance_evidence_json = snapshot_json
    submission.acceptance_evidence_hash = snapshot_hash
    submission.acceptance_recorded_at = submission.acceptance_recorded_at or now_datetime()
    receipt = next((a for a in snapshot["artifacts"] if a["role"] in {"RECEIPT", "ACKNOWLEDGEMENT"}), None)
    if receipt and receipt.get("file_url"):
        submission.acknowledgement_file = receipt["file_url"]


def _apply_result(submission, result: SubmissionResult, *, reconciled: bool = False):
    allowed = {"ACCEPTED", "REJECTED", "UNKNOWN", "SUBMITTING"}
    status = str(result.status or "UNKNOWN").upper()
    if status not in allowed:
        frappe.throw(f"Adapter returned unsupported submission status: {status}")
    submission.status = status
    if result.external_id:
        submission.external_reference = result.external_id
    if status == "ACCEPTED":
        _persist_acceptance_evidence(submission, result)
        if not submission.submitted_at:
            submission.submitted_at = now_datetime()
    if reconciled:
        submission.last_reconciled_at = now_datetime()
    submission.save(ignore_permissions=True)
    return submission


def submit_submission(name: str):
    submission = frappe.get_doc("VN Submission", name)
    if submission.status == "UNKNOWN":
        frappe.throw("UNKNOWN submission must be reconciled before any further submit attempt")
    if submission.status != "READY":
        frappe.throw("Only READY submissions may be submitted")
    _, adapter = _load_endpoint(submission.endpoint, submission.company, "SUBMIT")
    envelope = _envelope(submission)
    attempt = _next_attempt(submission.name, "SUBMIT", envelope)
    submission.status = "SUBMITTING"
    submission.save(ignore_permissions=True)
    try:
        result = adapter.submit(envelope)
    except AmbiguousTransportError as exc:
        _finish_attempt(attempt, "UNKNOWN", error=exc)
        submission.status = "UNKNOWN"
        submission.save(ignore_permissions=True)
        return submission
    except Exception as exc:
        _finish_attempt(attempt, "FAILED", error=exc)
        submission.status = "READY"
        submission.save(ignore_permissions=True)
        raise
    _finish_attempt(attempt, "SUCCESS" if result.status != "UNKNOWN" else "UNKNOWN", result=result)
    return _apply_result(submission, result)


def reconcile_submission(name: str):
    submission = frappe.get_doc("VN Submission", name)
    if submission.status not in {"UNKNOWN", "SUBMITTING"}:
        frappe.throw("Only UNKNOWN or SUBMITTING submissions require reconciliation")
    _, adapter = _load_endpoint(submission.endpoint, submission.company, "RECONCILE")
    envelope = _envelope(submission)
    attempt = _next_attempt(submission.name, "RECONCILE", envelope)
    try:
        result = adapter.reconcile(envelope)
    except Exception as exc:
        _finish_attempt(attempt, "FAILED", error=exc)
        raise
    outcome = "UNKNOWN" if str(result.status).upper() == "UNKNOWN" else "SUCCESS"
    _finish_attempt(attempt, outcome, result=result)
    return _apply_result(submission, result, reconciled=True)


@frappe.whitelist()
def create_submission(**kwargs):
    if not frappe.has_permission("VN Submission", ptype="create"):
        frappe.throw("Not permitted to create VN Submission", frappe.PermissionError)
    return prepare_submission(**kwargs).as_dict()


@frappe.whitelist()
def submit(name: str):
    if not frappe.has_permission("VN Submission", ptype="write", doc=name):
        frappe.throw("Not permitted to submit VN Submission", frappe.PermissionError)
    return submit_submission(name).as_dict()


@frappe.whitelist()
def reconcile(name: str):
    if not frappe.has_permission("VN Submission", ptype="write", doc=name):
        frappe.throw("Not permitted to reconcile VN Submission", frappe.PermissionError)
    return reconcile_submission(name).as_dict()
