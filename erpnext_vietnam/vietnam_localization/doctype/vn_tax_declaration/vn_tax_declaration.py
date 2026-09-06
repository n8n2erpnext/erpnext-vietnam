from __future__ import annotations

import json

import frappe
from frappe.model.document import Document
from frappe.utils import getdate

from erpnext_vietnam.declarations.canonical import payload_hash
from erpnext_vietnam.declarations.registry import TAX_FORMS

TRANSITIONS = {
    "Draft": {"Prepared", "Voided"},
    "Prepared": {"Reviewed", "Voided"},
    "Reviewed": {"Released", "Voided"},
    "Released": set(),
    "Voided": set(),
}
IMMUTABLE_RELEASED = {
    "company", "declaration_type", "period_type", "from_date", "to_date", "schema_version",
    "legal_instrument", "calculation_snapshot_json", "calculation_snapshot_hash",
    "declaration_json", "declaration_hash", "adapter_version", "adapter_status",
    "adapter_payload_json", "adapter_payload_hash", "source_count", "warning_json",
}


class VNTaxDeclaration(Document):
    def validate(self):
        if self.declaration_type not in TAX_FORMS:
            frappe.throw(f"Unsupported declaration type: {self.declaration_type}")
        spec = TAX_FORMS[self.declaration_type]
        if self.period_type not in spec.period_types:
            frappe.throw(f"{spec.code} does not support period type {self.period_type}")
        if getdate(self.from_date) > getdate(self.to_date):
            frappe.throw("From Date cannot be after To Date")
        self._validate_json_and_hashes()
        self._validate_transition_and_immutability()

    def _validate_json_and_hashes(self):
        try:
            snapshot = json.loads(self.calculation_snapshot_json or "{}")
            declaration = json.loads(self.declaration_json or "{}")
            adapter = json.loads(self.adapter_payload_json or "{}")
            warnings = json.loads(self.warning_json or "[]")
        except json.JSONDecodeError:
            frappe.throw("Declaration JSON fields must contain valid JSON")
        if not isinstance(warnings, list):
            frappe.throw("Warnings JSON must be a JSON array")
        self.calculation_snapshot_hash = payload_hash(snapshot)
        self.declaration_hash = payload_hash(declaration)
        self.adapter_payload_hash = payload_hash(adapter)
        self.adapter_version = adapter.get("adapter_version") or self.adapter_version
        self.adapter_status = "Ready" if adapter.get("ready") is True else "Needs Review"
        if self.status in {"Reviewed", "Released"} and self.adapter_status != "Ready":
            frappe.throw("Tax declaration cannot be Reviewed or Released until the statutory adapter is Ready")
        if self.declaration_type == "01_GTGT":
            self.source_count = len(declaration.get("source_documents") or [])
        else:
            self.source_count = len(declaration.get("source_salary_slips") or [])

    def _validate_transition_and_immutability(self):
        if self.is_new():
            if self.status not in {"Draft", "Prepared"}:
                frappe.throw("New tax declarations may start only as Draft or Prepared")
            return
        old_status = self.get_db_value("status")
        if old_status and self.status != old_status and self.status not in TRANSITIONS.get(old_status, set()):
            frappe.throw(f"Invalid declaration status transition: {old_status} -> {self.status}")
        if old_status == "Released":
            changed = [field for field in IMMUTABLE_RELEASED if self.has_value_changed(field)]
            if changed:
                frappe.throw("Released tax declaration is immutable. Changed: " + ", ".join(sorted(changed)))

    def on_trash(self):
        if self.status not in {"Draft", "Voided"}:
            frappe.throw("Prepared, Reviewed and Released tax declarations cannot be deleted; void them instead")
