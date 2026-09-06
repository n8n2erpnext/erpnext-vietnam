import json
import unittest
from pathlib import Path

from erpnext_vietnam.accounting.catalog_data import load_tt99_catalog, validate_catalog

ROOT = Path(__file__).parents[1]
EXPECTED_SHA256 = "2f8edab015d1291675d58e9b4452641350a66a5b5d23f47c85ca6dfd9953c99d"


class TestTT99Catalog(unittest.TestCase):
    def setUp(self):
        self.data = load_tt99_catalog()
        self.rows = self.data["records"]
        self.by_code = {row["account_code"]: row for row in self.rows}

    def test_catalog_integrity(self):
        validate_catalog(self.data)
        self.assertEqual(len(self.rows), 184)
        self.assertEqual(len([r for r in self.rows if r["level"] == 1]), 71)
        self.assertEqual(self.data["effective_from"], "2026-01-01")
        self.assertEqual(self.data["source_sha256"], EXPECTED_SHA256)

    def test_known_statutory_anchors(self):
        expected = {
            "111": "Tiền mặt",
            "1331": "Thuế GTGT được khấu trừ của hàng hóa, dịch vụ",
            "33311": "Thuế GTGT đầu ra",
            "3383": "Bảo hiểm xã hội",
            "3384": "Bảo hiểm y tế",
            "3386": "Bảo hiểm thất nghiệp",
            "511": "Doanh thu bán hàng và cung cấp dịch vụ",
            "632": "Giá vốn hàng bán",
            "911": "Xác định kết quả kinh doanh",
        }
        for code, name in expected.items():
            self.assertEqual(self.by_code[code]["account_name_vi"], name)

    def test_hierarchy_anchors(self):
        self.assertEqual(self.by_code["1331"]["parent_code"], "133")
        self.assertEqual(self.by_code["33311"]["parent_code"], "3331")
        self.assertEqual(self.by_code["215121"]["parent_code"], "21512")
        self.assertEqual(self.by_code["215121"]["level"], 4)

    def test_source_page_range(self):
        pages = {row["source_printed_page"] for row in self.rows}
        self.assertEqual(min(pages), 34)
        self.assertEqual(max(pages), 44)

    def test_reference_doctype_is_read_only(self):
        p = ROOT / "erpnext_vietnam/vietnam_localization/doctype/vn_statutory_account/vn_statutory_account.json"
        doc = json.loads(p.read_text())
        perm = doc["permissions"][0]
        self.assertEqual(perm.get("read"), 1)
        self.assertFalse(perm.get("write", 0))
        self.assertFalse(perm.get("create", 0))
        self.assertFalse(perm.get("delete", 0))


if __name__ == "__main__":
    unittest.main()
