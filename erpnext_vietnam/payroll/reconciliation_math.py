from __future__ import annotations

from decimal import Decimal

from erpnext_vietnam.payroll.insurance_math import d, money

EMPLOYEE_CODES = ("BHXH_EE", "BHYT_EE", "BHTN_EE", "PIT_WITHHOLDING")
EMPLOYER_CODES = ("BHXH_ER", "BHYT_ER", "BHTN_ER", "OAI_ER")


def compare_amount(expected, actual, tolerance=1) -> dict:
    expected = money(expected)
    actual = money(actual)
    variance = money(actual - expected)
    tol = abs(d(tolerance))
    return {
        "expected": expected,
        "actual": actual,
        "variance": variance,
        "status": "MATCH" if abs(variance) <= tol else "VARIANCE",
    }


def summarize_reconciliation(rows: list[dict]) -> dict:
    employee_expected = sum((d(r.get("expected")) for r in rows if r.get("code") in EMPLOYEE_CODES), Decimal("0"))
    employee_actual = sum((d(r.get("actual")) for r in rows if r.get("code") in EMPLOYEE_CODES), Decimal("0"))
    employer_expected = sum((d(r.get("expected")) for r in rows if r.get("code") in EMPLOYER_CODES), Decimal("0"))
    statuses = {r.get("status") for r in rows}
    if "UNMAPPED" in statuses:
        status = "UNMAPPED"
    elif "VARIANCE" in statuses:
        status = "VARIANCE"
    elif "NO_EVIDENCE" in statuses:
        status = "NO_EVIDENCE"
    else:
        status = "MATCH"
    return {
        "employee_expected_total": money(employee_expected),
        "employee_actual_total": money(employee_actual),
        "employee_variance_total": money(employee_actual - employee_expected),
        "employer_expected_total": money(employer_expected),
        "status": status,
    }
