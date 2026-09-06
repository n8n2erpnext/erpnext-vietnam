from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import getdate

VALID_INDICATORS = {"23", "24", "23a", "24a", "26", "29", "30", "31", "32", "33", "32a", "32b", "34a"}


class VNVATReportingCategory(Document):
    def validate(self):
        if self.effective_to and getdate(self.effective_to) < getdate(self.effective_from):
            frappe.throw("Effective To cannot be before Effective From")
        for fieldname in ("value_indicator", "tax_indicator", "secondary_value_indicator", "secondary_tax_indicator"):
            value = self.get(fieldname)
            if value and value not in VALID_INDICATORS:
                frappe.throw(f"Unsupported 01/GTGT indicator {value} in {fieldname}")
        if self.direction == "Output" and self.value_indicator in {"23", "23a"}:
            frappe.throw("Output reporting categories cannot use input-VAT indicators")
        if self.direction == "Input" and self.value_indicator not in {"23", "23a"}:
            frappe.throw("Input reporting categories must map to [23] or [23a] semantics")
        if not self.is_new() and self.get_db_value("reporting_status") == "Released":
            changed = [
                field for field in (
                    "code", "reporting_status", "direction", "value_indicator", "tax_indicator", "secondary_value_indicator",
                    "secondary_tax_indicator", "treatment_constraint", "requires_reduction_annex",
                    "effective_from", "effective_to", "rule_set", "legal_instrument", "legal_reference_detail",
                ) if self.has_value_changed(field)
            ]
            if changed:
                frappe.throw("Released VAT reporting categories are immutable. Changed: " + ", ".join(sorted(changed)))

    def on_trash(self):
        if self.reporting_status == "Released":
            frappe.throw("Released VAT reporting categories cannot be deleted; supersede with a new effective-dated version")
