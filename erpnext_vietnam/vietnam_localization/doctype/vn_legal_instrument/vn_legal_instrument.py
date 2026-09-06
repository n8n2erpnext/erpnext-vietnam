from frappe.model.document import Document
from frappe.utils import getdate
import frappe

class VNLegalInstrument(Document):
	def validate(self):
		if self.effective_to and getdate(self.effective_to) < getdate(self.effective_from):
			frappe.throw("Effective To cannot be before Effective From")
