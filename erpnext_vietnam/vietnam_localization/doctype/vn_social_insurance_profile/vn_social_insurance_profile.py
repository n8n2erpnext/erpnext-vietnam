import frappe
from frappe.model.document import Document
from frappe.utils import getdate


def _overlaps(a1, a2, b1, b2):
    return (a2 is None or b1 <= a2) and (b2 is None or a1 <= b2)


class VNSocialInsuranceProfile(Document):
    def validate(self):
        if self.effective_to and getdate(self.effective_to) < getdate(self.effective_from):
            frappe.throw("Effective To cannot be before Effective From")
        if self.participate_bhtn and not self.wage_region and self.contribution_category == "Ordinary":
            frappe.throw("Wage Region is required for ordinary BHTN participation")
        a1 = getdate(self.effective_from); a2 = getdate(self.effective_to) if self.effective_to else None
        rows = frappe.get_all("VN Social Insurance Profile", filters={"employee": self.employee}, fields=["name", "effective_from", "effective_to"])
        for row in rows:
            if row.name == self.name:
                continue
            b1 = getdate(row.effective_from); b2 = getdate(row.effective_to) if row.effective_to else None
            if _overlaps(a1, a2, b1, b2):
                frappe.throw(f"Overlapping VN Social Insurance Profile exists: {row.name}")
