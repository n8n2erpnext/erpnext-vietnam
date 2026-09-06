import unittest

from erpnext_vietnam.setup.domain_profiles import DOMAIN_PROFILES, get_domain_profile, get_domain_profile_options


class TestDomainProfiles(unittest.TestCase):
    def test_codes_are_unique(self):
        codes = [profile.code for profile in DOMAIN_PROFILES]
        self.assertEqual(len(codes), len(set(codes)))

    def test_required_domains_exist(self):
        required = {"RETAIL", "MANUFACTURING", "REAL_ESTATE", "HOSPITALITY", "HEALTHCARE", "AGRICULTURE", "SOFTWARE_SAAS"}
        self.assertTrue(required.issubset({profile.code for profile in DOMAIN_PROFILES}))

    def test_unknown_profile_rejected(self):
        with self.assertRaises(ValueError):
            get_domain_profile("NOT_A_PROFILE")

    def test_serialized_options_keep_stable_codes(self):
        options = get_domain_profile_options()
        self.assertIn("RETAIL", {row["code"] for row in options})


if __name__ == "__main__":
    unittest.main()
