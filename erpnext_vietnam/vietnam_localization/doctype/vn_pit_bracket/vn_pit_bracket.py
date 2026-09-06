import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class VNPITBracket(Document):
    def validate(self):
        if self.effective_to and getdate(self.effective_to) < getdate(self.effective_from):
            frappe.throw("Effective To cannot be before Effective From")
        if self.upper_bound not in (None, "") and float(self.upper_bound) <= float(self.lower_bound or 0):
            frappe.throw("Upper Bound must be greater than Lower Bound")
        old = self.get_doc_before_save()
        if old and old.rule_status == "Released":
            locked = ("residency", "period_basis", "sequence", "lower_bound", "upper_bound", "rate_percent", "effective_from", "effective_to", "rule_set", "legal_instrument")
            if any(str(getattr(old, f, None)) != str(getattr(self, f, None)) for f in locked):
                frappe.throw("Released PIT bracket terms are immutable; publish a new bracket version instead")
