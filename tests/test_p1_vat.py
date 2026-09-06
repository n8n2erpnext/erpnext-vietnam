import unittest
from datetime import date
from decimal import Decimal

from erpnext_vietnam.legal.models import EffectiveRule
from erpnext_vietnam.vat.models import VATClassificationDefinition
from erpnext_vietnam.vat.resolver import VATClassificationError, resolve_vat, validate_classification


class TestP1VAT(unittest.TestCase):
    def base(self, **overrides):
        values = dict(code="X", treatment="STANDARD_10", statutory_rate=Decimal("10"), effective_from=date(2025, 7, 1), effective_to=None, temporary_reduction_eligible=False, rule_set="VAT-2025-2026-V1")
        values.update(overrides)
        return VATClassificationDefinition(**values)

    def test_zero_rate_is_not_non_taxable(self):
        a = resolve_vat(self.base(treatment="ZERO_RATE_0", statutory_rate=Decimal("0")), date(2026, 1, 1))
        b = resolve_vat(self.base(treatment="NON_TAXABLE", statutory_rate=Decimal("0")), date(2026, 1, 1))
        self.assertNotEqual(a.treatment, b.treatment)
        self.assertEqual(a.rate, b.rate)

    def test_temporary_reduction_is_effective_dated(self):
        cls = self.base(temporary_reduction_eligible=True)
        rule = EffectiveRule("VAT.TEMP_REDUCTION_RATE", date(2025, 7, 1), date(2026, 12, 31), Decimal("8"))
        self.assertEqual(resolve_vat(cls, date(2026, 9, 6), rule).treatment, "TEMP_REDUCED_8")
        self.assertEqual(resolve_vat(cls, date(2027, 1, 1), rule).treatment, "STANDARD_10")

    def test_ineligible_standard_stays_ten(self):
        cls = self.base(temporary_reduction_eligible=False)
        rule = EffectiveRule("VAT.TEMP_REDUCTION_RATE", date(2025, 7, 1), date(2026, 12, 31), Decimal("8"))
        self.assertEqual(resolve_vat(cls, date(2026, 9, 6), rule).rate, Decimal("10"))

    def test_invalid_rate_rejected(self):
        with self.assertRaises(VATClassificationError):
            validate_classification(self.base(statutory_rate=Decimal("8")))

    def test_snapshot_changes_when_temporary_rule_applies(self):
        cls = self.base(temporary_reduction_eligible=True)
        rule = EffectiveRule("VAT.TEMP_REDUCTION_RATE", date(2025, 7, 1), date(2026, 12, 31), Decimal("8"))
        self.assertNotEqual(resolve_vat(cls, date(2026, 1, 1), rule).snapshot_hash, resolve_vat(cls, date(2027, 1, 1), rule).snapshot_hash)


if __name__ == "__main__":
    unittest.main()
