import frappe
from frappe.model.document import Document

IMMUTABLE_FIELDS = {
    "submission", "attempt_no", "operation", "started_at", "request_hash",
}


class VNSubmissionAttempt(Document):
    def validate(self):
        if self.attempt_no < 1:
            frappe.throw("Attempt No must be at least 1")
        if self.completed_at and self.started_at and self.completed_at < self.started_at:
            frappe.throw("Completed At cannot be before Started At")
        if self.is_new():
            if self.outcome != "PENDING":
                frappe.throw("New submission attempts must start as PENDING")
            return
        old_outcome = self.get_db_value("outcome")
        if old_outcome != "PENDING":
            changed = [field for field in self.meta.get_valid_columns() if self.has_value_changed(field)]
            if changed:
                frappe.throw("Completed submission attempts are append-only and immutable")
        if old_outcome == "PENDING" and self.outcome not in {"PENDING", "SUCCESS", "FAILED", "UNKNOWN"}:
            frappe.throw("Invalid submission attempt outcome")
        changed_identity = [field for field in IMMUTABLE_FIELDS if self.has_value_changed(field)]
        if changed_identity:
            frappe.throw("Submission attempt identity cannot change: " + ", ".join(sorted(changed_identity)))

    def on_trash(self):
        frappe.throw("Submission attempts are audit records and cannot be deleted")
