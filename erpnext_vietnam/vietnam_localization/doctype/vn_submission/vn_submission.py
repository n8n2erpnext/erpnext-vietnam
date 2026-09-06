import hashlib
import json

import frappe
from frappe.model.document import Document

IMMUTABLE_AFTER_TRANSPORT = {
    "company", "submission_type", "endpoint", "source_doctype", "source_name", "rule_set",
    "rule_snapshot_hash", "schema_version", "payload_json", "payload_hash", "idempotency_key",
}
ACCEPTANCE_ARCHIVE_FIELDS = {
    "external_reference", "submitted_at", "acceptance_evidence_json", "acceptance_evidence_hash",
    "acceptance_recorded_at", "acknowledgement_file",
}
TRANSITIONS = {
    "DRAFT": {"READY", "CANCELLED"},
    "READY": {"SUBMITTING", "CANCELLED"},
    "SUBMITTING": {"READY", "ACCEPTED", "REJECTED", "UNKNOWN"},
    "UNKNOWN": {"ACCEPTED", "REJECTED", "CANCELLED"},
    "ACCEPTED": set(),
    "REJECTED": set(),
    "CANCELLED": set(),
}


class VNSubmission(Document):
    def validate(self):
        try:
            payload = json.loads(self.payload_json)
        except json.JSONDecodeError:
            frappe.throw("Canonical Payload JSON must be valid JSON")
        if not isinstance(payload, dict):
            frappe.throw("Canonical Payload JSON must contain an object")
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        self.payload_json = canonical
        self.payload_hash = hashlib.sha256(canonical.encode()).hexdigest()
        identity = "|".join([
            self.company or "", self.submission_type or "", self.endpoint or "",
            self.schema_version or "", self.payload_hash,
        ])
        self.idempotency_key = hashlib.sha256(identity.encode()).hexdigest()
        if self.is_new():
            if self.status != "DRAFT":
                frappe.throw("New submissions must start as DRAFT")
            return
        old_status = self.get_db_value("status")
        if old_status and self.status != old_status and self.status not in TRANSITIONS.get(old_status, set()):
            frappe.throw(f"Invalid submission status transition: {old_status} -> {self.status}")
        if old_status not in (None, "DRAFT", "READY"):
            changed = [field for field in IMMUTABLE_AFTER_TRANSPORT if self.has_value_changed(field)]
            if changed:
                frappe.throw("Submission identity/payload cannot change after transport has started: " + ", ".join(sorted(changed)))
        if old_status == "ACCEPTED" or self.get_db_value("acceptance_evidence_hash"):
            changed = [field for field in ACCEPTANCE_ARCHIVE_FIELDS if self.has_value_changed(field)]
            if changed:
                frappe.throw("Accepted submission archive evidence is immutable: " + ", ".join(sorted(changed)))

    def on_trash(self):
        if self.status != "DRAFT":
            frappe.throw("Only DRAFT submissions may be deleted")
