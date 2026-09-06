import json
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from erpnext_vietnam.vat.reconciliation_math import period_is_covered, summarize_vat_gl

ROOT = Path(__file__).parents[1]


class TestP1Reconciliation(unittest.TestCase):
    def mapping(self, account, start="2026-01-01", end=None):
        return {"account": account, "effective_from": start, "effective_to": end}

    def test_gl_signs_follow_vat_control_account_semantics(self):
        entries = [
            {"account": "VAT OUT", "posting_date": "2026-09-01", "debit": 0, "credit": 100},
            {"account": "VAT IN", "posting_date": "2026-09-01", "debit": 40, "credit": 0},
        ]
        out = summarize_vat_gl(entries, [self.mapping("VAT OUT")], [self.mapping("VAT IN")])
        self.assertEqual(out["output_vat_gl_movement"], Decimal("100"))
        self.assertEqual(out["input_vat_gl_movement"], Decimal("40"))
        self.assertEqual(out["net_vat_accounting_movement"], Decimal("60"))

    def test_effective_dated_mapping_is_applied_per_entry(self):
        entries = [
            {"account": "OLD", "posting_date": "2026-06-30", "debit": 0, "credit": 10},
            {"account": "NEW", "posting_date": "2026-07-01", "debit": 0, "credit": 20},
        ]
        mappings = [self.mapping("OLD", "2026-01-01", "2026-06-30"), self.mapping("NEW", "2026-07-01")]
        out = summarize_vat_gl(entries, mappings, [])
        self.assertEqual(out["output_vat_gl_movement"], Decimal("30"))
        self.assertEqual(out["ignored_entries"], 0)

    def test_ambiguous_account_is_excluded(self):
        entries = [{"account": "VAT", "posting_date": "2026-09-01", "debit": 5, "credit": 10}]
        mapping = [self.mapping("VAT")]
        out = summarize_vat_gl(entries, mapping, mapping)
        self.assertEqual(out["ambiguous_entries"], 1)
        self.assertEqual(out["net_vat_accounting_movement"], Decimal("0"))

    def test_period_coverage_detects_gap(self):
        self.assertFalse(period_is_covered([
            self.mapping("A", "2026-01-01", "2026-01-10"),
            self.mapping("B", "2026-01-12", "2026-01-31"),
        ], date(2026, 1, 1), date(2026, 1, 31)))
        self.assertTrue(period_is_covered([
            self.mapping("A", "2026-01-01", "2026-01-10"),
            self.mapping("B", "2026-01-11", "2026-01-31"),
        ], date(2026, 1, 1), date(2026, 1, 31)))

    def test_standard_report_is_read_only(self):
        report = json.loads((ROOT / "erpnext_vietnam/vietnam_localization/report/vn_vat_reconciliation/vn_vat_reconciliation.json").read_text())
        self.assertEqual(report["report_type"], "Script Report")
        self.assertEqual(report["ref_doctype"], "GL Entry")
        source = (ROOT / "erpnext_vietnam/vat/reconciliation.py").read_text()
        for forbidden in ("make_gl_entries", ".insert(", ".save(", "db_set("):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
