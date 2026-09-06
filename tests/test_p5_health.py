import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEALTH = (ROOT / "erpnext_vietnam/diagnostics/health.py").read_text()
PAGE = (ROOT / "erpnext_vietnam/vietnam_localization/page/vn_localization_health/vn_localization_health.js").read_text()


class TestP5Health(unittest.TestCase):
    def test_health_api_is_whitelisted_permission_guarded_and_read_only(self):
        self.assertIn('@frappe.whitelist()\ndef get_health', HEALTH)
        self.assertIn('frappe.has_permission("Company", ptype="read"', HEALTH)
        for forbidden in (".insert(", ".save(", "frappe.db.set_value", "frappe.db.commit"):
            self.assertNotIn(forbidden, HEALTH)
        self.assertIn('"read_only": True', HEALTH)

    def test_health_surfaces_core_readiness_dimensions(self):
        for marker in ("coa_mappings", "einvoice_profiles", "enabled_integration_endpoints", "enable_compliance_gateway", "hrms_installed", "production_endpoints"):
            self.assertIn(marker, HEALTH)
        self.assertIn("PRODUCTION_CERTIFICATION_MISSING", HEALTH)
        self.assertIn("EINVOICE_PROFILE_MISSING", HEALTH)

    def test_health_page_calls_read_only_api_and_links_setup(self):
        self.assertIn("erpnext_vietnam.diagnostics.health.get_health", PAGE)
        self.assertIn('frappe.set_route("vn-setup-wizard")', PAGE)
        self.assertIn("operational readiness only", PAGE)


if __name__ == "__main__":
    unittest.main()
