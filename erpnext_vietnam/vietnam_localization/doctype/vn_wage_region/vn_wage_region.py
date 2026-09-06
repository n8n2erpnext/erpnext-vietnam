import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class VNWageRegion(Document):
    def validate(self):
        if self.effective_to and getdate(self.effective_to) < getdate(self.effective_from):
            frappe.throw("Effective To cannot be before Effective From")
        if float(self.monthly_minimum_wage or 0) <= 0:
            frappe.throw("Monthly Minimum Wage must be positive")
        old = self.get_doc_before_save()
        if old and old.reference_status == "Released":
            locked = ("monthly_minimum_wage", "hourly_minimum_wage", "effective_from", "effective_to", "legal_instrument")
            if any(str(getattr(old, f, None)) != str(getattr(self, f, None)) for f in locked):
                frappe.throw("Released wage-region terms are immutable; publish a new version instead")
