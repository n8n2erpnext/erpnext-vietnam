from __future__ import annotations

import hashlib
import json

import frappe

from erpnext_vietnam.integration.certification import AdapterCertification, CertificationArtifact, certification_hash
from erpnext_vietnam.integration.registry import register

COUNT_DOCTYPES = ("GL Entry", "Journal Entry", "VN Integration Endpoint")


def _counts():
    return {doctype: frappe.db.count(doctype) for doctype in COUNT_DOCTYPES}


class _UATAdapter:
    channel = "E_INVOICE"
    capabilities = frozenset({"VALIDATE"})

    def __init__(self, adapter_id: str):
        self.adapter_id = adapter_id

    def validate(self, envelope):
        return None

    def submit(self, envelope):
        raise RuntimeError("P4E UAT adapter must never transport")

    def get_status(self, external_id):
        raise RuntimeError("P4E UAT adapter must never transport")

    def reconcile(self, envelope):
        raise RuntimeError("P4E UAT adapter must never transport")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_production_certification_rollback_uat(company: str) -> dict:
    before = _counts()
    result = {"company": company, "before_counts": before}
    try:
        uncertified = _UATAdapter("uat.uncertified.einvoice.v1")
        register(uncertified)
        blocked = False
        try:
            frappe.get_doc({
                "doctype": "VN Integration Endpoint", "endpoint_name": "P4E Uncertified Production",
                "company": company, "adapter": uncertified.adapter_id, "channel": "E_INVOICE",
                "environment": "PRODUCTION", "enabled": 1, "credential_reference": "secret-ref://uat",
                "capabilities_json": json.dumps(["VALIDATE"]), "timeout_seconds": 5,
            }).insert(ignore_permissions=True)
        except frappe.ValidationError:
            blocked = True
        if not blocked:
            frappe.throw("P4E UAT expected uncertified production adapter to be blocked")

        certified = _UATAdapter("uat.certified.einvoice.v1")
        certification = AdapterCertification(
            adapter_id=certified.adapter_id, channel="E_INVOICE", certification_version="uat-cert-v1",
            provider_name="UAT Provider", reviewed_on="2026-09-06",
            artifacts=(
                CertificationArtifact("TECHNICAL_CONTRACT", "uat://official-contract", "v1", _sha("contract-v1")),
                CertificationArtifact("PAYLOAD_SCHEMA", "uat://official-schema", "v1", _sha("schema-v1")),
            ),
        )
        register(certified, certification)
        endpoint = frappe.get_doc({
            "doctype": "VN Integration Endpoint", "endpoint_name": "P4E Certified Production",
            "company": company, "adapter": certified.adapter_id, "channel": "E_INVOICE",
            "environment": "PRODUCTION", "enabled": 1, "credential_reference": "secret-ref://uat",
            "capabilities_json": json.dumps(["VALIDATE"]), "timeout_seconds": 5,
        }).insert(ignore_permissions=True)
        expected_hash = certification_hash(certification)
        if endpoint.adapter_certification_version != certification.certification_version:
            frappe.throw("P4E UAT certification version was not pinned")
        if endpoint.adapter_certification_hash != expected_hash:
            frappe.throw("P4E UAT certification hash was not pinned")
        during = _counts()
        if during["GL Entry"] != before["GL Entry"] or during["Journal Entry"] != before["Journal Entry"]:
            frappe.throw("P4E UAT changed accounting entries")
        result.update({
            "uncertified_blocked": blocked, "certified_endpoint": endpoint.name,
            "certification_version": endpoint.adapter_certification_version,
            "certification_hash": endpoint.adapter_certification_hash, "during_counts": during,
        })
    finally:
        frappe.db.rollback()
    result["after_counts"] = _counts()
    result["rollback_clean"] = result["after_counts"] == before
    return result
