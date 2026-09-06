import json
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]


class TestP3Schema(unittest.TestCase):
    def test_p3_doctypes_exist(self):
        for slug, name in {
            "vn_tax_declaration": "VN Tax Declaration",
            "vn_social_insurance_export": "VN Social Insurance Export",
        }.items():
            path = ROOT / f"erpnext_vietnam/vietnam_localization/doctype/{slug}/{slug}.json"
            self.assertTrue(path.exists(), slug)
            self.assertEqual(json.loads(path.read_text())["name"], name)

    def test_form_registry_is_canonical_and_versioned(self):
        source = (ROOT / "erpnext_vietnam/declarations/registry.py").read_text()
        for code in ("01/GTGT", "05/KK-TNCN", "05/QTT-TNCN", "TK1-TS", "TK3-TS", "D02-LT"):
            self.assertIn(code, source)
        self.assertIn("canonical-v1", source)

    def test_preview_is_separate_from_persistence_and_transport(self):
        source = (ROOT / "erpnext_vietnam/declarations/service.py").read_text()
        self.assertIn("preview_tax_declaration", source)
        self.assertIn("create_tax_declaration", source)
        self.assertIn("preview_social_insurance_export", source)
        self.assertNotIn("requests.", source)
        self.assertNotIn("make_gl_entries", source)
        self.assertNotIn("VN Submission\"", source)

    def test_new_runtime_is_consumer_neutral(self):
        runtime = "\n".join(
            p.read_text(errors="ignore")
            for p in (ROOT / "erpnext_vietnam/declarations").glob("*.py")
        )
        self.assertNotIn("LightBI", runtime)


if __name__ == "__main__":
    unittest.main()

class TestP3PeriodContract(unittest.TestCase):
    def test_tax_periods_are_calendar_bounded(self):
        source = (ROOT / "erpnext_vietnam/declarations/service.py").read_text()
        self.assertIn("Month period must cover one full calendar month", source)
        self.assertIn("Quarter period must cover one full calendar quarter", source)
        self.assertIn("Year period must cover one full calendar year", source)
