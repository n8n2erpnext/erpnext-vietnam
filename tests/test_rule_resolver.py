import unittest
from datetime import date
from decimal import Decimal

from erpnext_vietnam.legal.models import EffectiveRule, LegalReference
from erpnext_vietnam.legal.resolver import RuleConflictError, select_rule, snapshot_hash


class TestRuleResolver(unittest.TestCase):
    def test_effective_date_selects_historical_rule(self):
        rules = [
            EffectiveRule("VAT_STANDARD", date(2025, 7, 1), date(2026, 6, 30), Decimal("0.10")),
            EffectiveRule("VAT_STANDARD", date(2026, 7, 1), None, Decimal("0.10")),
        ]
        self.assertEqual(select_rule(rules, "VAT_STANDARD", date(2026, 6, 30)).effective_from, date(2025, 7, 1))
        self.assertEqual(select_rule(rules, "VAT_STANDARD", date(2026, 7, 1)).effective_from, date(2026, 7, 1))

    def test_duplicate_release_is_rejected(self):
        rules = [
            EffectiveRule("X", date(2026, 1, 1), None, 1),
            EffectiveRule("X", date(2026, 1, 1), None, 2),
        ]
        with self.assertRaises(RuleConflictError):
            select_rule(rules, "X", date(2026, 9, 1))

    def test_snapshot_hash_is_stable(self):
        rule = EffectiveRule("PIT", date(2026, 1, 1), None, Decimal("0.05"), references=(LegalReference("109/2025/QH15"),))
        self.assertEqual(snapshot_hash(rule), snapshot_hash(rule))


if __name__ == "__main__":
    unittest.main()
