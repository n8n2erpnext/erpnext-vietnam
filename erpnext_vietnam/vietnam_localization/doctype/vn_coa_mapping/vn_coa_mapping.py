import frappe
from frappe.model.document import Document
from frappe.utils import getdate

class VNCOAMapping(Document):
	def validate(self):
		if self.effective_to and getdate(self.effective_to) < getdate(self.effective_from):
			frappe.throw("Effective To cannot be before Effective From")
		if self.account and self.company:
			account_company = frappe.db.get_value("Account", self.account, "company")
			if account_company and account_company != self.company:
				frappe.throw("Mapped Account must belong to the selected Company")
