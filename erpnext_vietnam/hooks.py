app_name = "erpnext_vietnam"
app_title = "ERPNext Vietnam"
app_publisher = "n8n2erpnext"
app_description = "Universal Vietnam localization and compliance layer"
app_email = ""
app_license = ""

required_apps = ["erpnext"]

# HRMS is optional. Payroll/PIT/BHXH features activate only when HRMS is installed.

# P0 intentionally contains no product-specific hooks.
# DocType event hooks are added only when their statutory contracts are implemented and tested.
# App-specific setup wizard: universal domain/accounting/compliance preset.
setup_wizard_requires = "assets/erpnext_vietnam/js/setup_wizard.js"
setup_wizard_stages = "erpnext_vietnam.setup.setup_wizard.get_setup_stages"


# Safe install lifecycle: seed reference profiles only.
after_install = "erpnext_vietnam.setup.install.after_install"

after_migrate = "erpnext_vietnam.setup.install.after_migrate"

# Additive P1/P2 hooks. ERPNext/HRMS remain the transaction, tax, payroll and GL engines.
doc_events = {
    "Item": {"validate": "erpnext_vietnam.vat.service.validate_item"},
    "Sales Invoice": {"validate": "erpnext_vietnam.vat.service.validate_sales_invoice"},
    "Purchase Invoice": {"validate": "erpnext_vietnam.vat.service.validate_purchase_invoice"},
    "Salary Slip": {
        "validate": "erpnext_vietnam.payroll.service.validate_salary_slip",
        "on_submit": "erpnext_vietnam.payroll.service.snapshot_salary_slip",
    },
}
