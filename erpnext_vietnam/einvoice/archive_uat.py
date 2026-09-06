from __future__ import annotations

import hashlib
import json
import os

import frappe

from erpnext_vietnam.declarations.canonical import canonical_json, payload_hash
from erpnext_vietnam.einvoice.gateway import queue_einvoice, reconcile_einvoice, submit_einvoice
from erpnext_vietnam.einvoice.lifecycle import operation_idempotency_key
from erpnext_vietnam.einvoice.uat import _settings
from erpnext_vietnam.integration.adapters.sandbox import sandbox_einvoice_adapter

COUNT_DOCTYPES = (
    "GL Entry", "Journal Entry", "File", "VN Localization Settings", "VN Integration Endpoint",
    "VN E-Invoice Profile", "VN E-Invoice", "VN Submission", "VN Submission Attempt",
)


def _counts():
    return {doctype: frappe.db.count(doctype) for doctype in COUNT_DOCTYPES}


def _file_bytes(file_url: str) -> bytes:
    name = frappe.db.get_value("File", {"file_url": file_url}, "name")
    if not name:
        frappe.throw(f"P4D UAT cannot resolve archived File for {file_url}")
    content = frappe.get_doc("File", name).get_content()
    return content.encode("utf-8") if isinstance(content, str) else bytes(content)




def _cleanup_artifacts(file_urls: list[str]) -> bool:
    from frappe.utils.file_manager import delete_file

    paths = []
    for file_url in file_urls:
        filename = file_url.rsplit("/", 1)[-1]
        path = frappe.get_site_path("private", "files", filename)
        paths.append(path)
        delete_file(file_url)
        if os.path.exists(path):
            os.remove(path)
    return all(not os.path.exists(path) for path in paths)


def run_einvoice_archive_rollback_uat(sales_invoice: str) -> dict:
    invoice = frappe.get_doc("Sales Invoice", sales_invoice)
    if invoice.docstatus != 1:
        frappe.throw("P4D UAT requires a submitted Sales Invoice")
    company = invoice.company
    before = _counts()
    sandbox_einvoice_adapter.reset()
    file_urls: list[str] = []
    physical_artifacts_clean = False
    result = {"sales_invoice": sales_invoice, "company": company, "before_counts": before}
    try:
        _settings(company)
        endpoint = frappe.get_doc({
            "doctype": "VN Integration Endpoint", "endpoint_name": "P4D Archive Rollback UAT",
            "company": company, "adapter": "sandbox.einvoice.v1", "channel": "E_INVOICE",
            "environment": "SANDBOX", "enabled": 1,
            "capabilities_json": json.dumps(["VALIDATE", "SUBMIT", "RECONCILE"]), "timeout_seconds": 5,
        }).insert(ignore_permissions=True)
        profile = frappe.get_doc({
            "doctype": "VN E-Invoice Profile", "profile_name": "P4D Sandbox Archive", "company": company,
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
        revision = int(frappe.db.get_value(
            "VN E-Invoice", {"sales_invoice": invoice.name}, "revision", order_by="revision desc"
        ) or 0) + 2000
        einvoice = frappe.get_doc({
            "doctype": "VN E-Invoice", "company": company, "sales_invoice": invoice.name,
            "profile": profile.name, "invoice_type": "VAT_INVOICE", "revision": revision,
            "status": "PREPARED", "schema_version": "VN-EINVOICE-CANONICAL-2026-01",
            "canonical_payload_json": canonical_json(base_payload),
            "issue_idempotency_key": operation_idempotency_key(company, invoice.name, "ISSUE", revision),
        }).insert(ignore_permissions=True)
        einvoice, submission = queue_einvoice(einvoice.name)
        einvoice, submission = submit_einvoice(einvoice.name)
        if einvoice.status != "UNKNOWN":
            frappe.throw("P4D UAT expected synthetic timeout to yield UNKNOWN")
        einvoice, submission = reconcile_einvoice(einvoice.name)
        if einvoice.status != "ACCEPTED" or submission.status != "ACCEPTED":
            frappe.throw("P4D UAT reconciliation did not resolve ACCEPTED")
        if not submission.acceptance_evidence_json or not submission.acceptance_evidence_hash:
            frappe.throw("P4D UAT missing accepted-provider evidence snapshot")
        evidence = json.loads(submission.acceptance_evidence_json)
        artifacts = {a["role"]: a for a in evidence.get("artifacts", [])}
        final_xml = artifacts.get("FINAL_XML")
        receipt = artifacts.get("RECEIPT")
        if not final_xml or not final_xml.get("file_url") or not receipt or not receipt.get("file_url"):
            frappe.throw("P4D UAT missing private final XML or receipt artifact")
        file_urls[:] = [final_xml["file_url"], receipt["file_url"]]
        final_bytes = _file_bytes(final_xml["file_url"])
        final_hash = hashlib.sha256(final_bytes).hexdigest()
        if final_hash != final_xml["sha256"] or einvoice.final_xml_sha256 != final_hash:
            frappe.throw("P4D UAT final XML SHA-256 does not match archived bytes")
        if einvoice.final_xml_file != final_xml["file_url"] or submission.acknowledgement_file != receipt["file_url"]:
            frappe.throw("P4D UAT artifact URLs were not propagated to archive fields")
        archive = json.loads(einvoice.archive_snapshot_json or "{}")
        if payload_hash(archive) != einvoice.archive_snapshot_hash:
            frappe.throw("P4D UAT e-invoice archive snapshot hash mismatch")
        if archive.get("acceptance_evidence_hash") != submission.acceptance_evidence_hash:
            frappe.throw("P4D UAT archive is not chained to submission evidence hash")
        required = (einvoice.provider_request_id, einvoice.provider_invoice_id, einvoice.tax_authority_code,
                    einvoice.signing_certificate_serial, einvoice.accepted_at, einvoice.archive_locked_at)
        if not all(required):
            frappe.throw("P4D UAT accepted evidence was not propagated to e-invoice archive metadata")

        einvoice_immutable = False
        einvoice.final_xml_sha256 = "0" * 64
        try:
            einvoice.save(ignore_permissions=True)
        except frappe.ValidationError:
            einvoice_immutable = True
        if not einvoice_immutable:
            frappe.throw("P4D UAT expected accepted e-invoice archive fields to be immutable")
        submission = frappe.get_doc("VN Submission", submission.name)
        submission_immutable = False
        submission.acceptance_evidence_hash = "0" * 64
        try:
            submission.save(ignore_permissions=True)
        except frappe.ValidationError:
            submission_immutable = True
        if not submission_immutable:
            frappe.throw("P4D UAT expected accepted submission evidence to be immutable")

        calls = sandbox_einvoice_adapter.submit_calls.get(submission.idempotency_key)
        if calls != 1:
            frappe.throw("P4D UAT detected duplicate provider submit call")
        during = _counts()
        if during["GL Entry"] != before["GL Entry"] or during["Journal Entry"] != before["Journal Entry"]:
            frappe.throw("P4D UAT changed accounting entries")
        result.update({
            "einvoice": einvoice.name, "submission": submission.name, "final_status": "ACCEPTED",
            "provider_submit_calls": calls, "provider_request_id": einvoice.provider_request_id,
            "provider_invoice_id": einvoice.provider_invoice_id, "tax_authority_code": einvoice.tax_authority_code,
            "final_xml_sha256": final_hash, "acceptance_evidence_hash": submission.get_db_value("acceptance_evidence_hash"),
            "archive_snapshot_hash": einvoice.get_db_value("archive_snapshot_hash"),
            "einvoice_archive_immutable": einvoice_immutable, "submission_evidence_immutable": submission_immutable,
            "during_counts": during,
        })
    finally:
        frappe.db.rollback()
        sandbox_einvoice_adapter.reset()
        _cleanup_artifacts(file_urls)
    result["after_counts"] = _counts()
    result["rollback_clean"] = result["after_counts"] == before
    result["post_process_cleanup_required"] = bool(file_urls)
    return result


def cleanup_p4d_uat_artifacts() -> dict:
    from pathlib import Path
    from frappe.utils.file_manager import delete_file

    root = Path(frappe.get_site_path("private", "files")).resolve()
    removed = []
    for path in sorted(root.glob("p4d-uat-*")):
        if not path.is_file():
            continue
        file_url = "/private/files/" + path.name
        delete_file(file_url)
        if path.exists():
            path.unlink()
        if not path.exists():
            removed.append(path.name)
    remaining = sorted(p.name for p in root.glob("p4d-uat-*") if p.is_file())
    return {"removed": removed, "remaining": remaining, "clean": not remaining}
