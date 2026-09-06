import frappe
from frappe.model.document import Document


class VNPayrollCalculationLine(Document):
    def validate(self):
        if not self.is_new():
            frappe.throw("VN Payroll Calculation Line is immutable evidence")

    def on_trash(self):
        frappe.throw("VN Payroll Calculation Line is immutable evidence")
