import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestSettingsEntry(unittest.TestCase):
    def test_global_defaults_custom_fields_are_app_owned_and_idempotent(self):
        source = (ROOT / "erpnext_vietnam/setup/custom_fields.py").read_text()
        self.assertIn('"Global Defaults"', source)
        self.assertIn('"vn_localization_section"', source)
        self.assertIn('"vn_open_localization_setup"', source)
        self.assertIn('"vn_open_localization_health"', source)
        self.assertIn("create_custom_fields(fields, update=True)", source)

    def test_global_defaults_js_routes_to_setup_and_health(self):
        hooks = (ROOT / "erpnext_vietnam/hooks.py").read_text()
        js = (ROOT / "erpnext_vietnam/public/js/global_defaults.js").read_text()
        self.assertIn('"Global Defaults": "public/js/global_defaults.js"', hooks)
        self.assertIn('frappe.set_route("vn-setup-wizard")', js)
        self.assertIn('frappe.set_route("vn-localization-health")', js)
        self.assertIn("erpnext_vietnam.diagnostics.health.get_health", js)
        self.assertNotIn("frappe.db.set_value", js)


if __name__ == "__main__":
    unittest.main()
