from __future__ import annotations

from datetime import date
from decimal import Decimal


def decimal_value(value) -> Decimal:
    return Decimal(str(value or 0))


def _date_value(value) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _active(account: str, posting_date, mappings: list[dict]) -> bool:
    when = _date_value(posting_date)
    for mapping in mappings:
        if mapping.get("account") != account:
            continue
        start = _date_value(mapping["effective_from"])
        end = _date_value(mapping["effective_to"]) if mapping.get("effective_to") else None
        if start <= when and (end is None or when <= end):
            return True
    return False


def summarize_vat_gl(entries: list[dict], output_mappings: list[dict], input_mappings: list[dict]) -> dict:
    output = Decimal("0")
    input_vat = Decimal("0")
    ignored = 0
    ambiguous = 0
    output_entries = 0
    input_entries = 0
    for row in entries:
        account = row.get("account")
        when = row.get("posting_date")
        is_output = _active(account, when, output_mappings)
        is_input = _active(account, when, input_mappings)
        if is_output and is_input:
            ambiguous += 1
            continue
        debit = decimal_value(row.get("debit"))
        credit = decimal_value(row.get("credit"))
        if is_output:
            output += credit - debit
            output_entries += 1
        elif is_input:
            input_vat += debit - credit
            input_entries += 1
        else:
            ignored += 1
    return {
        "output_vat_gl_movement": output,
        "input_vat_gl_movement": input_vat,
        "net_vat_accounting_movement": output - input_vat,
        "output_entries": output_entries,
        "input_entries": input_entries,
        "ambiguous_entries": ambiguous,
        "ignored_entries": ignored,
    }


def period_is_covered(mappings: list[dict], from_date, to_date) -> bool:
    start = _date_value(from_date)
    end = _date_value(to_date)
    intervals = []
    for mapping in mappings:
        left = max(start, _date_value(mapping["effective_from"]))
        right = min(end, _date_value(mapping["effective_to"])) if mapping.get("effective_to") else end
        if left <= right:
            intervals.append((left, right))
    if not intervals:
        return False
    intervals.sort()
    cursor = start
    for left, right in intervals:
        if left > cursor:
            return False
        if right >= cursor:
            cursor = right.fromordinal(right.toordinal() + 1)
        if cursor > end:
            return True
    return cursor > end
