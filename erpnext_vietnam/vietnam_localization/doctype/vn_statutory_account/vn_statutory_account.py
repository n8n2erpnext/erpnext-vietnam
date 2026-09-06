import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class VNStatutoryAccount(Document):
    def validate(self):
        if self.effective_to and getdate(self.effective_to) < getdate(self.effective_from):
            frappe.throw("Effective To cannot be before Effective From")
        if not self.is_new():
            before = self.get_doc_before_save()
            if before and before.reference_status == "Released":
                immutable = [
                    "record_key", "catalog_version", "accounting_regime", "account_code", "parent_code",
                    "account_name_vi", "account_level", "account_category", "effective_from", "effective_to",
                    "legal_instrument", "source_printed_page", "source_sha256",
                ]
                changed = [field for field in immutable if before.get(field) != self.get(field)]
                if changed:
                    frappe.throw("Released statutory account records are immutable; publish a new catalog version. Changed: " + ", ".join(changed))
