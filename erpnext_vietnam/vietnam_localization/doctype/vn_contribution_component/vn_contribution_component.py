import frappe
from frappe.model.document import Document
from frappe.utils import getdate

EMPLOYEE_SIDE_CODES = {"PIT_WITHHOLDING", "BHXH_EE", "BHYT_EE", "BHTN_EE"}


class VNContributionComponent(Document):
    def validate(self):
        if self.effective_to and getdate(self.effective_to) < getdate(self.effective_from):
            frappe.throw("Effective To cannot be before Effective From")
        if self.mapping_status == "Released" and self.contribution_code in EMPLOYEE_SIDE_CODES and not self.salary_component:
            frappe.throw("A released employee/PIT contribution mapping requires an HRMS Salary Component")
        if self.salary_component and not frappe.db.exists("DocType", "Salary Component"):
            frappe.throw("HRMS Salary Component is not available on this site")
        a1 = getdate(self.effective_from); a2 = getdate(self.effective_to) if self.effective_to else None
        rows = frappe.get_all("VN Contribution Component", filters={"company": self.company, "contribution_code": self.contribution_code, "mapping_status":["!=", "Retired"]}, fields=["name", "effective_from", "effective_to"])
        for row in rows:
            if row.name == self.name:
                continue
            b1 = getdate(row.effective_from); b2 = getdate(row.effective_to) if row.effective_to else None
            if (a2 is None or b1 <= a2) and (b2 is None or a1 <= b2):
                frappe.throw(f"Overlapping VN Contribution Component exists: {row.name}")
        if self.mapping_status == "Released" and self.salary_component and self.contribution_code in EMPLOYEE_SIDE_CODES:
            reused = frappe.get_all("VN Contribution Component", filters={"company": self.company, "salary_component": self.salary_component, "mapping_status": "Released", "contribution_code": ["in", list(EMPLOYEE_SIDE_CODES)]}, fields=["name", "contribution_code", "effective_from", "effective_to"])
            for row in reused:
                if row.name == self.name or row.contribution_code == self.contribution_code:
                    continue
                b1 = getdate(row.effective_from); b2 = getdate(row.effective_to) if row.effective_to else None
                if (a2 is None or b1 <= a2) and (b2 is None or a1 <= b2):
                    frappe.throw(f"Salary Component {self.salary_component} is already used by {row.contribution_code}; split employee statutory deductions for auditable reconciliation")
