import frappe
from frappe.model.document import Document

class VNSubmissionAttempt(Document):
	def validate(self):
		if self.attempt_no < 1:
			frappe.throw("Attempt No must be at least 1")
		if self.completed_at and self.started_at and self.completed_at < self.started_at:
			frappe.throw("Completed At cannot be before Started At")
