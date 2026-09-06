import json

import frappe
from frappe.model.document import Document

from erpnext_vietnam.declarations.canonical import payload_hash
from erpnext_vietnam.einvoice.lifecycle import transition_allowed

IMMUTABLE_AFTER_TRANSPORT = {
    "company", "sales_invoice", "profile", "invoice_type", "revision", "schema_version",
    "canonical_payload_json", "canonical_payload_hash", "issue_idempotency_key",
}
ACCEPTANCE_ARCHIVE_FIELDS = {
    "provider_request_id", "provider_invoice_id", "tax_authority_code", "final_xml_file",
    "final_xml_sha256", "rendering_file", "signing_certificate_serial", "provider_response_json",
    "issued_at", "accepted_at", "archive_snapshot_json", "archive_snapshot_hash", "archive_locked_at",
}


class VNEInvoice(Document):
    def validate(self):
        if self.revision < 1:
            frappe.throw("Revision must be at least 1")
        try:
            payload = json.loads(self.canonical_payload_json or "{}")
        except json.JSONDecodeError:
            frappe.throw("Canonical Payload JSON must be valid JSON")
        embedded_hash = payload.pop("payload_hash", None)
        computed_hash = payload_hash(payload)
        if embedded_hash and embedded_hash != computed_hash:
            frappe.throw("Canonical payload embedded hash does not match its content")
        self.canonical_payload_hash = computed_hash
        payload["payload_hash"] = computed_hash
        self.canonical_payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if self.status == "PREPARED" and payload.get("ready") is not True:
            frappe.throw("E-invoice cannot be Prepared until the canonical payload is Ready")
        duplicate = frappe.db.get_value(
            "VN E-Invoice",
            {"sales_invoice": self.sales_invoice, "revision": self.revision, "name": ["!=", self.name or ""]},
            "name",
        )
        if duplicate:
            frappe.throw("Only one VN E-Invoice is allowed per Sales Invoice revision")
        if self.is_new():
            if self.status not in {"DRAFT", "PREPARED"}:
                frappe.throw("New e-invoice companion may start only as Draft or Prepared")
            return
        old_status = self.get_db_value("status") or "DRAFT"
        if not transition_allowed(old_status, self.status):
            frappe.throw(f"Invalid e-invoice status transition: {old_status} -> {self.status}")
        if old_status not in {"DRAFT", "PREPARED"}:
            changed = [f for f in IMMUTABLE_AFTER_TRANSPORT if self.has_value_changed(f)]
            if changed:
                frappe.throw("E-invoice source/canonical payload is immutable after transport starts: " + ", ".join(sorted(changed)))
        if old_status in {"ACCEPTED", "ADJUSTED", "REPLACED", "CANCELLED"} or self.get_db_value("archive_snapshot_hash"):
            changed = [f for f in ACCEPTANCE_ARCHIVE_FIELDS if self.has_value_changed(f)]
            if changed:
                frappe.throw("Accepted e-invoice archive evidence is immutable: " + ", ".join(sorted(changed)))

    def on_trash(self):
        if self.status not in {"DRAFT", "PREPARED", "REJECTED"}:
            frappe.throw("Transported/accepted e-invoices cannot be deleted; use the statutory lifecycle")
