from __future__ import annotations

from collections import defaultdict
from decimal import Decimal


def d(value) -> Decimal:
    return Decimal(str(value or 0))


def aggregate_pit_evidence(rows: list[dict]) -> dict:
    totals = defaultdict(lambda: Decimal("0"))
    employees: dict[str, dict] = {}
    snapshot_hashes = set()
    source_slips = set()
    for row in rows:
        employee = row.get("employee")
        slip = row.get("salary_slip")
        line_type = row.get("line_type")
        amount = d(row.get("amount"))
        if row.get("snapshot_hash"):
            snapshot_hashes.add(row["snapshot_hash"])
        if slip:
            source_slips.add(slip)
        if line_type:
            totals[line_type] += amount
        if employee:
            bucket = employees.setdefault(employee, {"employee": employee, "salary_slips": set(), "totals": defaultdict(lambda: Decimal("0"))})
            if slip:
                bucket["salary_slips"].add(slip)
            if line_type:
                bucket["totals"][line_type] += amount
    normalized_employees = []
    for employee in sorted(employees):
        bucket = employees[employee]
        normalized_employees.append({
            "employee": employee,
            "salary_slips": sorted(bucket["salary_slips"]),
            "totals": {k: bucket["totals"][k] for k in sorted(bucket["totals"])},
        })
    return {
        "employee_count": len(employees),
        "salary_slip_count": len(source_slips),
        "snapshot_hashes": sorted(snapshot_hashes),
        "totals": {k: totals[k] for k in sorted(totals)},
        "employees": normalized_employees,
    }


def select_pit_totals(aggregate: dict) -> dict:
    totals = aggregate.get("totals", {})
    return {
        "taxable_income": d(totals.get("PIT_TAXABLE_INCOME")),
        "insurance_deduction": d(totals.get("PIT_INSURANCE_DEDUCTION")),
        "assessable_income": d(totals.get("PIT_ASSESSABLE_INCOME")),
        "pit_withheld": d(totals.get("PIT_WITHHOLDING")),
    }
