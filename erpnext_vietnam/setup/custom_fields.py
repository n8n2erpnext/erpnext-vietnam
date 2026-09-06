from __future__ import annotations


def sync_custom_fields():
    import frappe
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
            {"fieldname": "vn_vat_reporting_category", "label": "VN VAT Reporting Category", "fieldtype": "Link", "options": "VN VAT Reporting Category", "insert_after": "vn_vat_snapshot_hash"},
            {"fieldname": "vn_vat_reporting_snapshot_hash", "label": "VN VAT Reporting Snapshot Hash", "fieldtype": "Data", "read_only": 1, "hidden": 1, "insert_after": "vn_vat_reporting_category"},
        ],
        "Purchase Invoice Item": [
            {"fieldname": "vn_vat_classification", "label": "VN VAT Classification", "fieldtype": "Link", "options": "VN VAT Classification", "insert_after": "item_tax_rate"},
            {"fieldname": "vn_vat_treatment", "label": "VN VAT Treatment", "fieldtype": "Data", "read_only": 1, "insert_after": "vn_vat_classification"},
            {"fieldname": "vn_vat_rate", "label": "VN VAT Rate (%)", "fieldtype": "Float", "read_only": 1, "precision": 6, "insert_after": "vn_vat_treatment"},
            {"fieldname": "vn_input_vat_deduction_status", "label": "Input VAT Deduction Status", "fieldtype": "Select", "options": "Unknown\nEligible\nPartially Eligible\nNon-deductible", "default": "Unknown", "insert_after": "vn_vat_rate"},
            {"fieldname": "vn_input_vat_deductible_ratio", "label": "Input VAT Deductible Ratio (%)", "fieldtype": "Percent", "default": "100", "insert_after": "vn_input_vat_deduction_status"},
            {"fieldname": "vn_input_vat_evidence_reference", "label": "Input VAT Evidence Reference", "fieldtype": "Data", "insert_after": "vn_input_vat_deductible_ratio"},
            {"fieldname": "vn_vat_snapshot_hash", "label": "VN VAT Snapshot Hash", "fieldtype": "Data", "read_only": 1, "hidden": 1, "insert_after": "vn_input_vat_evidence_reference"},
            {"fieldname": "vn_vat_reporting_category", "label": "VN VAT Reporting Category", "fieldtype": "Link", "options": "VN VAT Reporting Category", "insert_after": "vn_vat_snapshot_hash"},
            {"fieldname": "vn_vat_reporting_snapshot_hash", "label": "VN VAT Reporting Snapshot Hash", "fieldtype": "Data", "read_only": 1, "hidden": 1, "insert_after": "vn_vat_reporting_category"},
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

    if frappe.db.exists("DocType", "Salary Component"):
        fields["Salary Component"] = [
            {"fieldname": "vn_compliance_review_status", "label": "VN Compliance Review", "fieldtype": "Select", "options": "Unreviewed\nReviewed", "default": "Unreviewed", "insert_after": "is_tax_applicable"},
            {"fieldname": "vn_pit_taxable", "label": "VN PIT Taxable", "fieldtype": "Check", "default": "0", "insert_after": "vn_compliance_review_status"},
            {"fieldname": "vn_pit_exemption_code", "label": "VN PIT Exemption Code", "fieldtype": "Data", "insert_after": "vn_pit_taxable"},
            {"fieldname": "vn_pit_taxable_ratio", "label": "VN PIT Taxable Ratio (%)", "fieldtype": "Percent", "default": "100", "insert_after": "vn_pit_exemption_code"},
            {"fieldname": "vn_bhxh_base_included", "label": "Include in BHXH Base", "fieldtype": "Check", "default": "0", "insert_after": "vn_pit_taxable_ratio"},
            {"fieldname": "vn_bhyt_base_included", "label": "Include in BHYT Base", "fieldtype": "Check", "default": "0", "insert_after": "vn_bhxh_base_included"},
            {"fieldname": "vn_bhtn_base_included", "label": "Include in BHTN Base", "fieldtype": "Check", "default": "0", "insert_after": "vn_bhyt_base_included"},
            {"fieldname": "vn_regular_stable_payment", "label": "Regular Stable Payment", "fieldtype": "Check", "default": "0", "insert_after": "vn_bhtn_base_included"},
            {"fieldname": "vn_legal_rule", "label": "VN Legal Rule", "fieldtype": "Data", "insert_after": "vn_regular_stable_payment"},
        ]

    if frappe.db.exists("DocType", "Salary Slip"):
        fields["Salary Slip"] = [
            {"fieldname": "vn_payroll_compliance_status", "label": "VN Payroll Compliance Status", "fieldtype": "Data", "read_only": 1, "insert_after": "net_pay"},
            {"fieldname": "vn_pit_calculated", "label": "VN PIT Calculated", "fieldtype": "Currency", "options": "currency", "read_only": 1, "insert_after": "vn_payroll_compliance_status"},
            {"fieldname": "vn_employee_insurance_total", "label": "VN Employee Insurance", "fieldtype": "Currency", "options": "currency", "read_only": 1, "insert_after": "vn_pit_calculated"},
            {"fieldname": "vn_employer_insurance_total", "label": "VN Employer Insurance", "fieldtype": "Currency", "options": "currency", "read_only": 1, "insert_after": "vn_employee_insurance_total"},
            {"fieldname": "vn_payroll_snapshot_hash", "label": "VN Payroll Snapshot Hash", "fieldtype": "Data", "read_only": 1, "hidden": 1, "insert_after": "vn_employer_insurance_total"},
        ]

    create_custom_fields(fields, update=True)
