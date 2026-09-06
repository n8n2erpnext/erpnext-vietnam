import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]


class TestInstallContract(unittest.TestCase):
    def test_after_install_only_seeds_profiles(self):
        source = (ROOT / "erpnext_vietnam" / "setup" / "install.py").read_text()
        self.assertIn("sync_business_profiles", source)
        self.assertNotIn("apply_localization_profile", source)
        self.assertNotIn("submit", source.lower())

    def test_setup_page_uses_existing_profile_api(self):
        js = (ROOT / "erpnext_vietnam/vietnam_localization/page/vn_setup_wizard/vn_setup_wizard.js").read_text()
        self.assertIn("erpnext_vietnam.setup.setup_wizard.get_domain_profile_options", js)
        self.assertNotIn("get_vn_business_profile_options", js)

    def test_preview_contract_exists(self):
        source = (ROOT / "erpnext_vietnam" / "setup" / "setup_wizard.py").read_text()
        self.assertIn("def preview_localization_profile", source)
        self.assertIn('"snapshot_hash"', source)
        self.assertIn('"changes"', source)


if __name__ == "__main__":
    unittest.main()
