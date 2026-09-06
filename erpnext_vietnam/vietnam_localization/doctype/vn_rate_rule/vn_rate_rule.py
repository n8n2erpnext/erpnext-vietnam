from frappe.model.document import Document
from frappe.utils import getdate
import frappe

class VNRateRule(Document):
	def validate(self):
		if self.effective_to and getdate(self.effective_to) < getdate(self.effective_from):
			frappe.throw("Effective To cannot be before Effective From")
		if self.value_type in {"Text", "JSON"} and not self.text_value:
			frappe.throw("Text / JSON Value is required for this value type")
		if not self.is_new() and self.get_db_value("rule_status") == "Released":
			for field in ("rule_set", "code", "effective_from", "effective_to", "priority", "legal_instrument"):
				if self.has_value_changed(field):
					frappe.throw("Released VN Rate Rule is immutable; create a new effective-dated rule")
