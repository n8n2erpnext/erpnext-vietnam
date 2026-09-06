import frappe
from frappe.model.document import Document
from frappe.utils import getdate

from erpnext_vietnam.accounting.roles import validate_statutory_role


class VNCOAMapping(Document):
    def validate(self):
        try:
            self.statutory_role = validate_statutory_role(self.statutory_role)
        except ValueError as exc:
            frappe.throw(str(exc))
        if self.effective_to and getdate(self.effective_to) < getdate(self.effective_from):
            frappe.throw("Effective To cannot be before Effective From")
        if self.account and self.company:
            account_company = frappe.db.get_value("Account", self.account, "company")
            if account_company and account_company != self.company:
                frappe.throw("Mapped Account must belong to the selected Company")
        for row in frappe.get_all("VN COA Mapping", filters={"company": self.company, "statutory_role": self.statutory_role, "accounting_regime": self.accounting_regime}, fields=["name", "effective_from", "effective_to"]):
            if row.name == self.name:
                continue
            a1, a2 = getdate(self.effective_from), getdate(self.effective_to) if self.effective_to else None
            b1, b2 = getdate(row.effective_from), getdate(row.effective_to) if row.effective_to else None
            if (a2 is None or b1 <= a2) and (b2 is None or a1 <= b2):
                frappe.throw(f"Overlapping VN COA Mapping exists: {row.name}")
