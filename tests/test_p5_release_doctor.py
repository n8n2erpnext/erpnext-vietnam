import unittest
from pathlib import Path

from erpnext_vietnam.diagnostics.compatibility import is_supported, parse_major

ROOT = Path(__file__).resolve().parents[1]
DOCTOR = (ROOT / "erpnext_vietnam/diagnostics/release_doctor.py").read_text()


class TestP5ReleaseDoctor(unittest.TestCase):
    def test_compatibility_parser_targets_v16(self):
        self.assertEqual(parse_major("16.17.0"), 16)
        self.assertTrue(is_supported("frappe", "16.17.0"))
        self.assertTrue(is_supported("erpnext", "16.16.0"))
        self.assertTrue(is_supported("hrms", "16.5.4"))
        self.assertFalse(is_supported("frappe", "17.0.0"))

    def test_doctor_is_read_only_and_checks_release_contract(self):
        for forbidden in (".insert(", ".save(", "frappe.db.set_value", "frappe.db.commit", "frappe.db.rollback"):
            self.assertNotIn(forbidden, DOCTOR)
        for marker in ("CRITICAL_DOCTYPES", "CRITICAL_PAGES", "BUSINESS_PROFILE_SEEDS", "SETUP_SNAPSHOT_INTEGRITY", "NO_SANDBOX_PRODUCTION_ENDPOINT", "PRODUCTION_CERTIFICATION_PINS"):
            self.assertIn(marker, DOCTOR)
        self.assertIn('"read_only": True', DOCTOR)

    def test_doctor_api_requires_system_permission(self):
        self.assertIn('@frappe.whitelist()\ndef doctor', DOCTOR)
        self.assertIn('frappe.has_permission("System Settings", ptype="read")', DOCTOR)


if __name__ == "__main__":
    unittest.main()
