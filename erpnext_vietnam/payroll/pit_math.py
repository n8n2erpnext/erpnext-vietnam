from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

ZERO = Decimal("0")
ONE_VND = Decimal("1")


def d(value) -> Decimal:
    return Decimal(str(value or 0))


def money(value) -> Decimal:
    return d(value).quantize(ONE_VND, rounding=ROUND_HALF_UP)


def progressive_tax(assessable_income, brackets: list[dict]) -> Decimal:
    income = max(ZERO, d(assessable_income))
    tax = ZERO
    for row in sorted(brackets, key=lambda x: int(x.get("sequence") or 0)):
        lower = d(row.get("lower_bound"))
        upper_raw = row.get("upper_bound")
        upper = d(upper_raw) if upper_raw not in (None, "") else None
        rate = d(row.get("rate_percent")) / Decimal("100")
        if income <= lower:
            continue
        taxable_slice = income - lower if upper is None else min(income, upper) - lower
        if taxable_slice > 0:
            tax += taxable_slice * rate
    return money(tax)


def resident_assessable_income(taxable_income, insurance_deduction, personal_deduction, dependent_deduction) -> Decimal:
    return money(max(ZERO, d(taxable_income) - d(insurance_deduction) - d(personal_deduction) - d(dependent_deduction)))


def nonresident_salary_tax(taxable_income, rate_percent) -> Decimal:
    return money(max(ZERO, d(taxable_income)) * d(rate_percent) / Decimal("100"))
