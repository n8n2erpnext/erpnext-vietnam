import frappe
from frappe.model.document import Document
from frappe.utils import getdate

from erpnext_vietnam.vat.models import VATClassificationDefinition
from erpnext_vietnam.vat.resolver import VATClassificationError, validate_classification


class VNVATClassification(Document):
    def validate(self):
        definition = VATClassificationDefinition(
            code=self.code,
            treatment=self.treatment,
            statutory_rate=self.statutory_rate,
            effective_from=getdate(self.effective_from),
            effective_to=getdate(self.effective_to) if self.effective_to else None,
            temporary_reduction_eligible=bool(self.temporary_reduction_eligible),
            rule_set=self.rule_set,
            legal_instrument=self.legal_instrument,
            legal_reference_detail=self.legal_reference_detail,
        )
        try:
            validate_classification(definition)
        except VATClassificationError as exc:
            frappe.throw(str(exc))

        if not self.is_new() and frappe.db.get_value(self.doctype, self.name, "classification_status") == "Released":
            immutable = ["code", "treatment", "statutory_rate", "temporary_reduction_eligible", "effective_from", "effective_to", "rule_set", "legal_instrument"]
            before = self.get_doc_before_save()
            if before:
                changed = [field for field in immutable if before.get(field) != self.get(field)]
                if changed:
                    frappe.throw("Released VAT classifications are immutable; create a new version instead. Changed: " + ", ".join(changed))
