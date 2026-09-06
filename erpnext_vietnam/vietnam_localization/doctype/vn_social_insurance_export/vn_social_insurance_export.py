from __future__ import annotations

import json

import frappe
from frappe.model.document import Document
from frappe.utils import getdate

from erpnext_vietnam.declarations.canonical import payload_hash
from erpnext_vietnam.declarations.registry import BHXH_FORMS

TRANSITIONS = {
    "Draft": {"Prepared", "Voided"},
    "Prepared": {"Reviewed", "Voided"},
    "Reviewed": {"Released", "Voided"},
    "Released": set(),
    "Voided": set(),
}
IMMUTABLE_RELEASED = {
    "company", "export_type", "subject_doctype", "subject_name", "from_date", "to_date",
    "schema_version", "source_reference", "source_url", "source_sha256",
    "canonical_payload_json", "payload_hash", "adapter_version", "adapter_status",
    "adapter_payload_json", "adapter_payload_hash", "source_count", "warning_json",
}


class VNSocialInsuranceExport(Document):
    def validate(self):
        if self.export_type not in BHXH_FORMS:
            frappe.throw(f"Unsupported social-insurance export type: {self.export_type}")
        if getdate(self.from_date) > getdate(self.to_date):
            frappe.throw("From Date cannot be after To Date")
        self._validate_payload()
        self._validate_transition_and_immutability()

    def _validate_payload(self):
        try:
            payload = json.loads(self.canonical_payload_json or "{}")
            adapter = json.loads(self.adapter_payload_json or "{}")
            warnings = json.loads(self.warning_json or "[]")
        except json.JSONDecodeError:
            frappe.throw("Social-insurance export JSON fields must contain valid JSON")
        if not isinstance(warnings, list):
            frappe.throw("Warnings JSON must be a JSON array")
        self.payload_hash = payload_hash(payload)
        self.adapter_payload_hash = payload_hash(adapter)
        self.adapter_version = adapter.get("adapter_version") or self.adapter_version
        self.adapter_status = "Ready" if adapter.get("ready") is True else "Needs Review"
        if self.status in {"Reviewed", "Released"} and self.adapter_status != "Ready":
            frappe.throw("Social-insurance export cannot be Reviewed or Released until the statutory adapter is Ready")
        if self.export_type == "D02_LT":
            self.source_count = len(payload.get("rows") or [])
        else:
            self.source_count = 1

    def _validate_transition_and_immutability(self):
        if self.is_new():
            if self.status not in {"Draft", "Prepared"}:
                frappe.throw("New social-insurance exports may start only as Draft or Prepared")
            return
        old_status = self.get_db_value("status")
        if old_status and self.status != old_status and self.status not in TRANSITIONS.get(old_status, set()):
            frappe.throw(f"Invalid export status transition: {old_status} -> {self.status}")
        if old_status == "Released":
            changed = [field for field in IMMUTABLE_RELEASED if self.has_value_changed(field)]
            if changed:
                frappe.throw("Released social-insurance export is immutable. Changed: " + ", ".join(sorted(changed)))

    def on_trash(self):
        if self.status not in {"Draft", "Voided"}:
            frappe.throw("Prepared, Reviewed and Released social-insurance exports cannot be deleted; void them instead")
