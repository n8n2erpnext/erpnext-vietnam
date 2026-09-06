from __future__ import annotations


def sync_custom_fields():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    fields = {
        "Item": [
            {"fieldname": "vn_vat_classification", "label": "VN VAT Classification", "fieldtype": "Link", "options": "VN VAT Classification", "insert_after": "taxes"},
        ],
        "Sales Invoice Item": [
            {"fieldname": "vn_vat_classification", "label": "VN VAT Classification", "fieldtype": "Link", "options": "VN VAT Classification", "insert_after": "item_tax_rate"},
            {"fieldname": "vn_vat_treatment", "label": "VN VAT Treatment", "fieldtype": "Data", "read_only": 1, "insert_after": "vn_vat_classification"},
            {"fieldname": "vn_vat_rate", "label": "VN VAT Rate (%)", "fieldtype": "Float", "read_only": 1, "precision": 6, "insert_after": "vn_vat_treatment"},
            {"fieldname": "vn_vat_snapshot_hash", "label": "VN VAT Snapshot Hash", "fieldtype": "Data", "read_only": 1, "hidden": 1, "insert_after": "vn_vat_rate"},
        ],
        "Purchase Invoice Item": [
            {"fieldname": "vn_vat_classification", "label": "VN VAT Classification", "fieldtype": "Link", "options": "VN VAT Classification", "insert_after": "item_tax_rate"},
            {"fieldname": "vn_vat_treatment", "label": "VN VAT Treatment", "fieldtype": "Data", "read_only": 1, "insert_after": "vn_vat_classification"},
            {"fieldname": "vn_vat_rate", "label": "VN VAT Rate (%)", "fieldtype": "Float", "read_only": 1, "precision": 6, "insert_after": "vn_vat_treatment"},
            {"fieldname": "vn_input_vat_deduction_status", "label": "Input VAT Deduction Status", "fieldtype": "Select", "options": "Unknown\nEligible\nPartially Eligible\nNon-deductible", "default": "Unknown", "insert_after": "vn_vat_rate"},
            {"fieldname": "vn_input_vat_deductible_ratio", "label": "Input VAT Deductible Ratio (%)", "fieldtype": "Percent", "default": "100", "insert_after": "vn_input_vat_deduction_status"},
            {"fieldname": "vn_input_vat_evidence_reference", "label": "Input VAT Evidence Reference", "fieldtype": "Data", "insert_after": "vn_input_vat_deductible_ratio"},
            {"fieldname": "vn_vat_snapshot_hash", "label": "VN VAT Snapshot Hash", "fieldtype": "Data", "read_only": 1, "hidden": 1, "insert_after": "vn_input_vat_evidence_reference"},
        ],
        "Sales Invoice": [
            {"fieldname": "vn_vat_validation_status", "label": "VN VAT Validation Status", "fieldtype": "Data", "read_only": 1, "hidden": 1, "insert_after": "item_wise_tax_details"},
            {"fieldname": "vn_vat_snapshot_hash", "label": "VN VAT Snapshot Hash", "fieldtype": "Data", "read_only": 1, "hidden": 1, "insert_after": "vn_vat_validation_status"},
        ],
        "Purchase Invoice": [
            {"fieldname": "vn_vat_validation_status", "label": "VN VAT Validation Status", "fieldtype": "Data", "read_only": 1, "hidden": 1, "insert_after": "item_wise_tax_details"},
            {"fieldname": "vn_vat_snapshot_hash", "label": "VN VAT Snapshot Hash", "fieldtype": "Data", "read_only": 1, "hidden": 1, "insert_after": "vn_vat_validation_status"},
        ],
    }
    create_custom_fields(fields, update=True)
