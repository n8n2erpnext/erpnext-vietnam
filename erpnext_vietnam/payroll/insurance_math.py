from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

ONE_VND = Decimal("1")
ZERO = Decimal("0")


def d(value) -> Decimal:
    return Decimal(str(value or 0))


def money(value) -> Decimal:
    return d(value).quantize(ONE_VND, rounding=ROUND_HALF_UP)


def clamp_contribution_base(raw_base, floor_amount=None, ceiling_amount=None) -> Decimal:
    raw = d(raw_base)
    if raw <= 0:
        return ZERO
    result = raw
    if floor_amount not in (None, ""):
        result = max(result, d(floor_amount))
    if ceiling_amount not in (None, ""):
        result = min(result, d(ceiling_amount))
    return money(result)


def contribution_amount(base_amount, rate_percent) -> Decimal:
    return money(d(base_amount) * d(rate_percent) / Decimal("100"))
