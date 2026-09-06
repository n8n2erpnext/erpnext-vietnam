import frappe
from frappe.model.document import Document


class VNBusinessProfile(Document):
    def validate(self):
        if not self.is_new():
            old = self.get_doc_before_save()
            if old and old.profile_code != self.profile_code:
                frappe.throw("Profile Code is immutable.")
