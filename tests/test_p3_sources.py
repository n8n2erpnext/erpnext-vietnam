import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]


class TestP3Sources(unittest.TestCase):
    def test_tax_source_is_official_and_pinned(self):
        source = (ROOT / "erpnext_vietnam/setup/p3_seed.py").read_text()
        self.assertIn("89/2026/TT-BTC", source)
        self.assertIn("datafiles.chinhphu.vn", source)
        self.assertIn("952c45ffc0f10bfc176bd9ae6b3d204fd3a034294ee270278957b9c11e1471dc", source)

    def test_bhxh_form_sources_are_official_and_pinned(self):
        source = (ROOT / "erpnext_vietnam/declarations/bhxh.py").read_text()
        self.assertIn("baohiemxahoi.gov.vn", source)
        for digest in (
            "629efd6340e2baef003dd4a7069f287140abda468a8d6a8aa9f69dd56e6ef225",
            "f045e830adb50555529e0a17eb4ddcf39c1e6da54e1098abd4ba25c3309220bd",
            "29ce038a9de1a04cfd7b75f26bd5366bb04282f3bb16b70dcd781f0c39850a0d",
        ):
            self.assertIn(digest, source)


if __name__ == "__main__":
    unittest.main()
