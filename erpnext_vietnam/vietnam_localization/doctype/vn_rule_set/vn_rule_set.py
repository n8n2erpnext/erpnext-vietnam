from frappe.model.document import Document
from frappe.utils import getdate
import frappe

class VNRuleSet(Document):
	def validate(self):
		if self.effective_to and getdate(self.effective_to) < getdate(self.effective_from):
			frappe.throw("Effective To cannot be before Effective From")
		if not self.is_new() and self.get_db_value("rule_status") == "Released":
			protected = ("code", "effective_from", "effective_to")
			for field in protected:
				if self.has_value_changed(field):
					frappe.throw("Released VN Rule Set identity/effective dates are immutable; create a new version instead")
