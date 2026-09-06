from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

import frappe
from frappe.utils import getdate

from erpnext_vietnam.accounting.roles import PAYROLL_PAYABLE_ROLES
from erpnext_vietnam.accounting.service import resolve_coa_mapping
from erpnext_vietnam.payroll.insurance_math import d, money
from erpnext_vietnam.payroll.reconciliation_math import EMPLOYEE_CODES, EMPLOYER_CODES, compare_amount, summarize_reconciliation


def _settings(company: str):
    name = frappe.db.get_value("VN Localization Settings", {"company": company}, "name")
    return frappe.get_doc("VN Localization Settings", name) if name else None


def resolve_component_mapping(company: str, contribution_code: str, when):
    when = getdate(when)
    rows = frappe.get_all(
        "VN Contribution Component",
        filters={"company": company, "contribution_code": contribution_code, "mapping_status": "Released", "effective_from": ["<=", when]},
        fields=["name", "salary_component", "effective_from", "effective_to", "rule_set"],
        order_by="effective_from desc",
    )
    rows = [r for r in rows if not r.effective_to or getdate(r.effective_to) >= when]
    if not rows:
        return None
    best_date = getdate(rows[0].effective_from)
    tied = [r for r in rows if getdate(r.effective_from) == best_date]
    if len(tied) > 1:
        frappe.throw(f"Ambiguous VN Contribution Component for {company} / {contribution_code} on {when}")
    return rows[0]


def _evidence_lines(salary_slip: str):
    return frappe.get_all(
        "VN Payroll Calculation Line",
        filters={"salary_slip": salary_slip},
        fields=["line_type", "amount", "snapshot_hash", "rule_code", "rule_set", "legal_instrument"],
        order_by="line_type asc",
    )


def _actual_deductions(doc) -> dict[str, Decimal]:
    result: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for row in doc.deductions:
        if row.salary_component:
            result[row.salary_component] += d(row.amount)
    return result


def reconcile_salary_slip(salary_slip: str, tolerance=1) -> dict:
    doc = frappe.get_doc("Salary Slip", salary_slip)
    when = getdate(doc.end_date or doc.posting_date)
    evidence = _evidence_lines(doc.name)
    by_type = {row.line_type: row for row in evidence}
    snapshot_hashes = sorted({row.snapshot_hash for row in evidence if row.snapshot_hash})
    warnings = []
    if not evidence:
        return {
            "salary_slip": doc.name, "employee": doc.employee, "company": doc.company,
            "posting_date": when, "status": "NO_EVIDENCE", "rows": [],
            "warnings": ["No immutable VN Payroll Calculation Line evidence exists for this Salary Slip."],
        }
    if len(snapshot_hashes) != 1:
        warnings.append("Payroll evidence contains multiple snapshot hashes; manual review required.")

    actual = _actual_deductions(doc)
    rows = []
    for code in EMPLOYEE_CODES:
        expected = d(by_type.get(code).amount) if by_type.get(code) else Decimal("0")
        mapping = resolve_component_mapping(doc.company, code, when)
        if not mapping:
            rows.append({"code": code, "expected": money(expected), "actual": Decimal("0"), "variance": money(-expected), "status": "UNMAPPED", "salary_component": None})
            continue
        actual_amount = actual.get(mapping.salary_component, Decimal("0"))
        row = {"code": code, "salary_component": mapping.salary_component, **compare_amount(expected, actual_amount, tolerance)}
        rows.append(row)

    for code in EMPLOYER_CODES:
        expected = d(by_type.get(code).amount) if by_type.get(code) else Decimal("0")
        rows.append({"code": code, "expected": money(expected), "actual": None, "variance": None, "status": "EXPECTED_ONLY", "salary_component": None})

    summary = summarize_reconciliation(rows)
    if len(snapshot_hashes) != 1 and summary["status"] == "MATCH":
        summary["status"] = "EVIDENCE_CONFLICT"
    return {
        "salary_slip": doc.name, "employee": doc.employee, "company": doc.company,
        "posting_date": when, "snapshot_hash": snapshot_hashes[0] if len(snapshot_hashes) == 1 else None,
        "rows": rows, "warnings": warnings, **summary,
    }


def employer_accrual_preview(company: str, from_date, to_date) -> dict:
    from_date, to_date = getdate(from_date), getdate(to_date)
    settings = _settings(company)
    if not settings or not settings.enable_payroll_compliance:
        return {"company": company, "from_date": from_date, "to_date": to_date, "configured": False, "warnings": ["VN payroll compliance is not enabled for this Company."]}

    slips = frappe.get_all(
        "Salary Slip", filters={"company": company, "docstatus": 1, "end_date": ["between", [from_date, to_date]]},
        fields=["name", "employee", "end_date", "posting_date"], order_by="end_date asc, name asc",
    )
    payable_groups = defaultdict(lambda: Decimal("0"))
    unmapped = []
    included_slips = []
    for slip in slips:
        when = getdate(slip.end_date or slip.posting_date)
        evidence = _evidence_lines(slip.name)
        by_type = {row.line_type: row for row in evidence}
        if not evidence:
            unmapped.append({"salary_slip": slip.name, "reason": "NO_EVIDENCE"})
            continue
        included_slips.append(slip.name)
        for code in EMPLOYER_CODES:
            amount = d(by_type.get(code).amount) if by_type.get(code) else Decimal("0")
            if amount == 0:
                continue
            role = PAYROLL_PAYABLE_ROLES[code]
            mapping = resolve_coa_mapping(company, role, when, settings.accounting_regime)
            if not mapping:
                unmapped.append({"salary_slip": slip.name, "code": code, "role": role, "reason": "NO_COA_MAPPING"})
                continue
            payable_groups[(code, role, mapping.account)] += amount

    lines = [
        {"code": code, "statutory_role": role, "payable_account": account, "credit_amount": money(amount)}
        for (code, role, account), amount in sorted(payable_groups.items())
    ]
    total = money(sum((d(row["credit_amount"]) for row in lines), Decimal("0")))
    return {
        "company": company, "from_date": from_date, "to_date": to_date, "configured": True,
        "salary_slips": included_slips, "payable_lines": lines, "employer_contribution_total": total,
        "unmapped": unmapped, "expense_allocation_required": True,
        "read_only": True,
        "warnings": ["This is an accrual preview only. No Journal Entry is created or submitted. Expense-account allocation remains an explicit accounting decision."],
    }


@frappe.whitelist()
def get_payroll_reconciliation(company: str, from_date, to_date, employee: str | None = None):
    filters = {"company": company, "docstatus": 1, "end_date": ["between", [getdate(from_date), getdate(to_date)]]}
    if employee:
        filters["employee"] = employee
    slips = frappe.get_all("Salary Slip", filters=filters, fields=["name"], order_by="end_date asc, name asc")
    return [reconcile_salary_slip(row.name) for row in slips]


@frappe.whitelist()
def get_employer_accrual_preview(company: str, from_date, to_date):
    return employer_accrual_preview(company, from_date, to_date)
