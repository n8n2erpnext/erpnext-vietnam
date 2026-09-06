import json
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]


class TestP1Schema(unittest.TestCase):
    def test_vat_classification_doctype(self):
        p = ROOT / "erpnext_vietnam/vietnam_localization/doctype/vn_vat_classification/vn_vat_classification.json"
        doc = json.loads(p.read_text())
        fields = {f["fieldname"]: f for f in doc["fields"]}
        self.assertEqual(doc["name"], "VN VAT Classification")
        self.assertIn("NON_TAXABLE", fields["treatment"]["options"])
        self.assertIn("TEMP_REDUCED_8", fields["treatment"]["options"])

    def test_p1_uses_native_erpnext_tax_rate_for_validation_only(self):
        source = (ROOT / "erpnext_vietnam/vat/service.py").read_text()
        self.assertIn("item_tax_rate", source)
        self.assertNotIn("make_gl_entries", source)
        self.assertNotIn('db_set("item_tax_rate"', source)

    def test_hooks_are_additive(self):
        hooks = (ROOT / "erpnext_vietnam/hooks.py").read_text()
        self.assertNotIn("override_doctype_class", hooks)
        self.assertIn('"Sales Invoice": {"validate":', hooks)
        self.assertIn('"Purchase Invoice": {"validate":', hooks)

    def test_no_product_specific_runtime(self):
        runtime = "\n".join(p.read_text(errors="ignore") for p in (ROOT / "erpnext_vietnam").rglob("*.py"))
        self.assertNotIn("LightBI", runtime)

    def test_current_vat_amendment_chain_is_seeded(self):
        seed = (ROOT / "erpnext_vietnam/setup/p1_seed.py").read_text()
        for instrument in ("149/2025/QH15", "359/2025/NĐ-CP", "09/2026/QH16", "144/2026/NĐ-CP"):
            self.assertIn(instrument, seed)


if __name__ == "__main__":
    unittest.main()
