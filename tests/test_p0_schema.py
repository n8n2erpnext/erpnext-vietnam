import json
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1] / "erpnext_vietnam" / "vietnam_localization" / "doctype"


class TestP0Schema(unittest.TestCase):
    expected = {
        "VN Legal Instrument",
        "VN Rule Set",
        "VN Rate Rule",
        "VN Localization Settings",
        "VN COA Mapping",
        "VN Integration Endpoint",
        "VN Submission",
        "VN Submission Attempt",
    }

    def _docs(self):
        return [json.loads(p.read_text()) for p in ROOT.glob("*/*.json")]

    def test_all_foundation_doctypes_exist(self):
        names = {d["name"] for d in self._docs()}
        self.assertTrue(self.expected.issubset(names))

    def test_gateway_defaults_safe(self):
        endpoint = next(d for d in self._docs() if d["name"] == "VN Integration Endpoint")
        fields = {f["fieldname"]: f for f in endpoint["fields"]}
        self.assertEqual(fields["enabled"].get("default"), "0")
        self.assertEqual(fields["environment"]["options"].splitlines()[0], "SANDBOX")

    def test_submission_idempotency_key_unique(self):
        submission = next(d for d in self._docs() if d["name"] == "VN Submission")
        fields = {f["fieldname"]: f for f in submission["fields"]}
        self.assertEqual(fields["idempotency_key"].get("unique"), 1)
        self.assertEqual(fields["idempotency_key"].get("read_only"), 1)

    def test_hrms_is_not_hard_dependency(self):
        hooks = (Path(__file__).parents[1] / "erpnext_vietnam" / "hooks.py").read_text()
        self.assertIn('required_apps = ["erpnext"]', hooks)
        self.assertNotIn('required_apps = ["erpnext", "hrms"]', hooks)


if __name__ == "__main__":
    unittest.main()
