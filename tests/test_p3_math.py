import unittest
from decimal import Decimal

from erpnext_vietnam.declarations.canonical import canonical_json, payload_hash
from erpnext_vietnam.declarations.math import aggregate_pit_evidence, select_pit_totals


class TestP3Math(unittest.TestCase):
    def test_hash_is_order_independent_and_decimal_stable(self):
        a = {"b": Decimal("10.00"), "a": {"y": 2, "x": 1}}
        b = {"a": {"x": 1, "y": 2}, "b": Decimal("10.00")}
        self.assertEqual(canonical_json(a), canonical_json(b))
        self.assertEqual(payload_hash(a), payload_hash(b))

    def test_pit_evidence_aggregation(self):
        rows = [
            {"employee": "E1", "salary_slip": "S1", "line_type": "PIT_TAXABLE_INCOME", "amount": 30_000_000, "snapshot_hash": "h1"},
            {"employee": "E1", "salary_slip": "S1", "line_type": "PIT_WITHHOLDING", "amount": 635_000, "snapshot_hash": "h1"},
            {"employee": "E2", "salary_slip": "S2", "line_type": "PIT_TAXABLE_INCOME", "amount": 20_000_000, "snapshot_hash": "h2"},
            {"employee": "E2", "salary_slip": "S2", "line_type": "PIT_WITHHOLDING", "amount": 100_000, "snapshot_hash": "h2"},
        ]
        aggregate = aggregate_pit_evidence(rows)
        totals = select_pit_totals(aggregate)
        self.assertEqual(aggregate["employee_count"], 2)
        self.assertEqual(aggregate["salary_slip_count"], 2)
        self.assertEqual(totals["taxable_income"], Decimal("50000000"))
        self.assertEqual(totals["pit_withheld"], Decimal("735000"))


if __name__ == "__main__":
    unittest.main()
