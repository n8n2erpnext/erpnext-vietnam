app_name = "erpnext_vietnam"
app_title = "ERPNext Vietnam"
app_publisher = "n8n2erpnext"
app_description = "Universal Vietnam localization and compliance layer"
app_email = ""
app_license = ""

required_apps = ["erpnext", "hrms"]

# P0 intentionally contains no product-specific hooks.
# DocType event hooks are added only when their statutory contracts are implemented and tested.
# App-specific setup wizard: universal domain/accounting/compliance preset.
setup_wizard_requires = "assets/erpnext_vietnam/js/setup_wizard.js"
setup_wizard_stages = "erpnext_vietnam.setup.setup_wizard.get_setup_stages"

