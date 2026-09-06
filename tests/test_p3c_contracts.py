import json
import unittest
from pathlib import Path

from erpnext_vietnam.declarations.adapters.bhxh_qd505_1040 import (
    D02_COLUMNS, D02_HEADER_FIELDS, TK1_INDICATORS, TK3_INDICATORS,
    adapt_d02_lt, adapt_tk1_ts, adapt_tk3_ts,
)

ROOT = Path(__file__).parents[1]


class TestP3CContracts(unittest.TestCase):
    def test_bhxh_contracts_match_pinned_forms(self):
        self.assertEqual(set(D02_COLUMNS), {str(i) for i in range(1, 28)})
        for key in ("01", "02", "03", "04", "05", "06", "07", "08", "09.1", "09.2", "09.3", "10", "11.1", "11.2", "11.3", "11.4", "12", "13", "14.1", "14.2", "14.3", "14.4", "14.5", "15", "16", "17", "18", "19"):
            self.assertIn(key, TK1_INDICATORS)
        for key in ("01", "02", "03", "04", "05", "06", "07", "08", "09", "10.1", "10.2", "11", "12", "13"):
            self.assertIn(key, TK3_INDICATORS)

    def test_p3c_schema_has_reporting_taxonomy_and_adapter_snapshots(self):
        reporting = ROOT / "erpnext_vietnam/vietnam_localization/doctype/vn_vat_reporting_category/vn_vat_reporting_category.json"
        self.assertEqual(json.loads(reporting.read_text())["name"], "VN VAT Reporting Category")
        for slug in ("vn_tax_declaration", "vn_social_insurance_export"):
            data = json.loads((ROOT / f"erpnext_vietnam/vietnam_localization/doctype/{slug}/{slug}.json").read_text())
            fields = {row["fieldname"] for row in data["fields"]}
            self.assertTrue({"adapter_version", "adapter_status", "adapter_payload_json", "adapter_payload_hash"} <= fields)

    def test_tt89_reporting_categories_are_explicit_and_additive(self):
        seed = (ROOT / "erpnext_vietnam/setup/p3_seed.py").read_text()
        for code in (
            "TT89-OUT-NON-TAXABLE", "TT89-OUT-ZERO", "TT89-OUT-FIVE", "TT89-OUT-TEN",
            "TT89-OUT-TEMP-EIGHT", "TT89-OUT-NOT-DECLARED", "TT89-OUT-NOT-IN-TAX-BASE",
            "TT89-OUT-OUTSIDE-SCOPE", "TT89-IN-DOMESTIC", "TT89-IN-IMPORTED",
        ):
            self.assertIn(code, seed)
        self.assertIn('"23", "24", "23a", "24a"', seed)
        self.assertIn('"32", "33", None, None, "TEMP_REDUCED_8", 1', seed)

    def test_tt89_period_and_historical_guards(self):
        registry = (ROOT / "erpnext_vietnam/declarations/registry.py").read_text()
        adapter = (ROOT / "erpnext_vietnam/declarations/adapters/tax_tt89.py").read_text()
        self.assertIn('"05_KK_TNCN": FormSpec("05/KK-TNCN", "Periodic PIT withholding declaration", "TAX", ("Quarter",)', registry)
        self.assertIn('code in {"01/GTGT", "05/KK-TNCN"}', adapter)
        self.assertIn('code == "05/QTT-TNCN"', adapter)
        self.assertIn('from_date.year < 2026', adapter)

    def test_bhxh_synthetic_vectors_can_reach_ready_without_guessing(self):
        tk1 = adapt_tk1_ts({
            "form_code": "TK1-TS", "source_sha256": "x",
            "employee": {"name": "EMP-1", "employee_name": "NGUYEN VAN A", "gender": "Nam", "date_of_birth": "1990-01-01", "cell_number": "0900", "current_address": "1 Street"},
            "social_insurance_profile": {},
            "statutory_inputs": {"filing_mode": "New", "indicators": {
                "04": "Việt Nam", "05": "Kinh", "06": "012345678901",
                "09.1": "Phường A", "09.2": "Quận B", "09.3": "TP C",
                "11.2": "Phường A", "11.3": "Quận B", "11.4": "TP C",
            }},
        })
        self.assertTrue(tk1["ready"], tk1["missing_required"])

        tk3 = adapt_tk3_ts({
            "form_code": "TK3-TS", "source_sha256": "y",
            "company": {"name": "ACME", "company_name": "ACME", "tax_id": "0312345678", "phone_no": "028123", "email": "a@example.com"},
            "statutory_inputs": {"indicators": {
                "02": "", "04": "1 Registered St", "05": "Công ty TNHH", "06": "Dịch vụ",
                "07": "1 Contact St", "10.1": "0123456789", "10.2": "Sở KHĐT",
            }},
        })
        self.assertTrue(tk3["ready"], tk3["missing_required"])

        explicit = {str(i): None for i in range(8, 27)}
        explicit.update({"6": "012345678901", "7": "Kỹ sư", "12": 20_000_000, "25": "2026-07", "27": "HĐLĐ 01/2026"})
        d02 = adapt_d02_lt({
            "form_code": "D02-LT", "company": "ACME",
            "company_master": {"name": "ACME", "company_name": "ACME", "tax_id": "0312345678", "phone_no": "028123", "email": "a@example.com"},
            "statutory_inputs": {"header": {
                "document_number": "01/2026", "unit_code": "UNIT01", "address": "1 Street",
                "signed_place": "TP C", "signed_date": "2026-09-30",
            }},
            "rows": [{
                "employee": "EMP-1", "employee_name": "NGUYEN VAN A", "salary_slip": "SS-1", "snapshot_hash": "h",
                "employee_master": {"employee_name": "NGUYEN VAN A", "date_of_birth": "1990-01-01", "gender": "Nam", "designation": "Kỹ sư"},
                "social_insurance_profile": {"social_insurance_number": "1234567890"},
            }],
            "statutory_rows": [{"source_salary_slip": "SS-1", "columns": explicit}],
        })
        self.assertEqual(set(d02["indicators"]), set(D02_HEADER_FIELDS))
        self.assertTrue(d02["ready"], d02["missing_required"])


    def test_preview_and_create_permissions_guard_underlying_evidence(self):
        service = (ROOT / "erpnext_vietnam/declarations/service.py").read_text()
        for token in (
            'has_permission("GL Entry", ptype="read")',
            'has_permission("Salary Slip", ptype="read")',
            'has_permission("Employee", ptype="read")',
            'has_permission("VN Tax Declaration", ptype="create")',
            'has_permission("VN Social Insurance Export", ptype="create")',
        ):
            self.assertIn(token, service)

    def test_released_reporting_taxonomy_is_immutable(self):
        controller = (ROOT / "erpnext_vietnam/vietnam_localization/doctype/vn_vat_reporting_category/vn_vat_reporting_category.py").read_text()
        self.assertIn('get_db_value("reporting_status") == "Released"', controller)
        self.assertIn('"reporting_status"', controller)
        self.assertIn("def on_trash", controller)


    def test_adapters_have_no_transport_side_effects(self):
        text = "\n".join((ROOT / path).read_text() for path in (
            "erpnext_vietnam/declarations/adapters/tax_tt89.py",
            "erpnext_vietnam/declarations/adapters/bhxh_qd505_1040.py",
            "erpnext_vietnam/declarations/adapters/base.py",
        ))
        for forbidden in ("requests.", "httpx.", "urllib.request", 'get_doc("VN Submission"', 'doctype": "VN Submission"'):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
