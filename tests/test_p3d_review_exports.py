import io
import json
import unittest
import zipfile
from xml.etree import ElementTree as ET

from erpnext_vietnam.declarations.canonical import payload_hash
from erpnext_vietnam.declarations.exporters.review import (
    ReviewExportError,
    build_review_export,
    export_filename,
)


def ready_adapter(form_code, indicators=None, rows=None):
    payload = {
        "form_code": form_code,
        "adapter_version": "test-v1",
        "legal_source": "TEST-LEGAL-SOURCE",
        "indicators": indicators or {},
        "rows": rows or [],
        "missing_required": [],
        "warnings": ["engineering-reviewed synthetic vector"],
        "source_refs": [{"source": "synthetic"}],
        "ready": True,
    }
    payload["payload_hash"] = payload_hash(payload)
    return payload


class TestP3DReviewExports(unittest.TestCase):
    def test_all_six_form_vectors_serialize_deterministically(self):
        vectors = {
            "01/GTGT": ready_adapter("01/GTGT", {key: 0 for key in (
                "21","22","23","24","23a","24a","25","26","27","28","29","30","31","32","33",
                "32a","32b","34a","34","35","36","37","38","39a","40a","40b","40","41","42","43"
            )}),
            "05/KK-TNCN": ready_adapter("05/KK-TNCN", {str(i): 0 for i in range(15, 46)}),
            "05/QTT-TNCN": ready_adapter("05/QTT-TNCN", {str(i): 0 for i in range(15, 46)}),
            "TK1-TS": ready_adapter("TK1-TS", {key: "reviewed" for key in (
                "01","02","03","04","05","06","07","08","09.1","09.2","09.3","10","11.1","11.2","11.3","11.4",
                "12","13","14.1","14.2","14.3","14.4","14.5","15","16","17","18","19"
            )}),
            "TK3-TS": ready_adapter("TK3-TS", {key: "reviewed" for key in (
                "01","02","03","04","05","06","07","08","09","10.1","10.2","11","12","13"
            )}),
            "D02-LT": ready_adapter("D02-LT", {
                "unit_name": "Synthetic Co", "document_number": "D02-001", "unit_code": "UNIT-1",
                "tax_id": "0000000000", "address": "Hanoi", "phone": "000", "email": "a@example.test",
                "signed_place": "Hanoi", "signed_date": "2026-09-06",
            }, rows=[{"columns": {str(i): (i if i == 1 else f"v{i}") for i in range(1, 28)}, "source_salary_slip": "SS-TEST"}]),
        }
        for form_code, adapter in vectors.items():
            with self.subTest(form_code=form_code):
                meta = {"document_name": "TEST-001", "company": "Synthetic Co"}
                xml_a = build_review_export(adapter, "xml", meta)
                xml_b = build_review_export(adapter, "xml", meta)
                xlsx_a = build_review_export(adapter, "xlsx", meta)
                xlsx_b = build_review_export(adapter, "xlsx", meta)
                self.assertEqual(xml_a, xml_b)
                self.assertEqual(xlsx_a, xlsx_b)
                root = ET.fromstring(xml_a)
                self.assertEqual(root.tag, "VNStatutoryReviewPackage")
                self.assertEqual(root.attrib["schema"], "vn-statutory-review-v1")
                with zipfile.ZipFile(io.BytesIO(xlsx_a)) as archive:
                    names = set(archive.namelist())
                    self.assertIn("xl/workbook.xml", names)
                    self.assertIn("xl/worksheets/sheet1.xml", names)
                    self.assertIn("xl/worksheets/sheet5.xml", names)
                    workbook = archive.read("xl/workbook.xml").decode()
                    self.assertIn("Indicators", workbook)
                    self.assertIn("Review Notes", workbook)

    def test_exporter_fails_closed_for_unready_or_tampered_adapter(self):
        adapter = ready_adapter("01/GTGT", {"21": False})
        adapter["ready"] = False
        with self.assertRaises(ReviewExportError):
            build_review_export(adapter, "xml")
        adapter = ready_adapter("01/GTGT", {"21": False})
        adapter["indicators"]["21"] = True
        with self.assertRaises(ReviewExportError):
            build_review_export(adapter, "xlsx")

    def test_filename_is_safe_and_review_labeled(self):
        name = export_filename("05/QTT-TNCN", "DECL / 001", "xlsx")
        self.assertEqual(name, "05-QTT-TNCN-DECL-001-review.xlsx")

    def test_service_download_contract_is_permission_and_ready_gated(self):
        source = PathLike.read_service()
        self.assertIn('doc.has_permission("read")', source)
        self.assertIn('doc.adapter_status != "Ready"', source)
        self.assertIn('package_purpose": "human_review_not_direct_government_upload"', source)
        self.assertIn("download_tax_declaration_review", source)
        self.assertIn("download_social_insurance_export_review", source)

    def test_doctype_ui_only_exposes_review_exports_when_ready(self):
        from pathlib import Path
        for slug in ("vn_tax_declaration", "vn_social_insurance_export"):
            source = Path(f"erpnext_vietnam/vietnam_localization/doctype/{slug}/{slug}.js").read_text()
            self.assertIn('adapter_status !== "Ready"', source)
            self.assertIn('status === "Voided"', source)
            self.assertIn('__("Review XLSX")', source)
            self.assertIn('__("Review XML")', source)
            self.assertIn('/api/method/', source)


class PathLike:
    @staticmethod
    def read_service():
        from pathlib import Path
        return Path("erpnext_vietnam/declarations/service.py").read_text()


if __name__ == "__main__":
    unittest.main()
