import frappe
from frappe.model.document import Document


class VNEInvoiceProfile(Document):
    def validate(self):
        if self.enabled and not self.endpoint:
            frappe.throw("Enabled e-invoice profile requires an Integration Endpoint")
        if self.endpoint:
            endpoint = frappe.db.get_value(
                "VN Integration Endpoint", self.endpoint,
                ["company", "channel", "enabled"], as_dict=True,
            )
            if not endpoint:
                frappe.throw("E-invoice Integration Endpoint does not exist")
            if endpoint.company != self.company:
                frappe.throw("E-invoice endpoint must belong to the same Company")
            if endpoint.channel != "E_INVOICE":
                frappe.throw("E-invoice profile requires an E_INVOICE channel endpoint")
            if self.enabled and not endpoint.enabled:
                frappe.throw("Enabled e-invoice profile requires an enabled endpoint")
        if self.signing_mode != "UNSPECIFIED" and not self.signing_reference:
            frappe.throw("Signing mode requires a signing reference; raw private keys must not be stored here")
