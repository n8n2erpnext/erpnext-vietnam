from __future__ import annotations

from collections import Counter

import frappe
from frappe.utils import getdate

from erpnext_vietnam.declarations.math import aggregate_pit_evidence, select_pit_totals
from erpnext_vietnam.vat.reconciliation import build_vat_reconciliation


def _submitted_invoices(company: str, from_date, to_date) -> list[dict]:
    rows = []
    for doctype in ("Sales Invoice", "Purchase Invoice"):
        for row in frappe.get_all(
            doctype,
            filters={"company": company, "docstatus": 1, "posting_date": ["between", [from_date, to_date]]},
            fields=["name", "posting_date", "vn_vat_snapshot_hash", "vn_vat_validation_status"],
            order_by="posting_date asc, name asc",
            limit_page_length=0,
        ):
            rows.append({
                "doctype": doctype,
                "name": row.name,
                "date": str(row.posting_date),
                "snapshot_hash": row.vn_vat_snapshot_hash,
                "validation_status": row.vn_vat_validation_status,
            })
    return rows


def build_01_gtgt(company: str, from_date, to_date) -> dict:
    from_date, to_date = getdate(from_date), getdate(to_date)
    reconciliation = build_vat_reconciliation(company, from_date, to_date)
    sources = _submitted_invoices(company, from_date, to_date)
    warnings = list(reconciliation.get("warnings") or [])
    if not reconciliation.get("configured"):
        warnings.append("Vietnam VAT localization is not configured for this Company.")
    missing = sum(1 for row in sources if not row.get("snapshot_hash"))
    if missing:
        warnings.append(f"{missing} submitted VAT source invoices do not carry a VN VAT snapshot hash.")
    return {
        "form_code": "01/GTGT",
        "schema_version": "canonical-v1",
        "company": company,
        "period": {"from_date": str(from_date), "to_date": str(to_date)},
        "calculation_basis": "ERPNext native GL + immutable VN VAT evidence",
        "accounting_summary": reconciliation.get("gl") or {},
        "invoice_coverage": reconciliation.get("invoice_coverage") or {},
        "input_vat_evidence": reconciliation.get("purchase_input_evidence") or {},
        "source_documents": sources,
        "warnings": sorted(set(warnings)),
        "adapter_ready": False,
        "review_required": True,
        "scope_note": "Canonical preparation model only; official indicator mapping/export adapter is versioned separately.",
    }


def _submitted_payroll(company: str, from_date, to_date) -> tuple[list[dict], list[dict], list[str]]:
    slips = frappe.get_all(
        "Salary Slip",
        filters={"company": company, "docstatus": 1, "end_date": ["between", [from_date, to_date]]},
        fields=["name", "employee", "end_date", "vn_payroll_snapshot_hash", "vn_payroll_compliance_status"],
        order_by="end_date asc, name asc",
        limit_page_length=0,
    )
    names = [row.name for row in slips]
    evidence = []
    if names:
        evidence = frappe.get_all(
            "VN Payroll Calculation Line",
            filters={"salary_slip": ["in", names]},
            fields=["salary_slip", "employee", "posting_date", "line_type", "base_amount", "amount", "snapshot_hash", "rule_code", "rule_set", "legal_instrument"],
            order_by="posting_date asc, salary_slip asc, line_type asc",
            limit_page_length=0,
        )
    by_slip = Counter(row.salary_slip for row in evidence)
    warnings = []
    for slip in slips:
        if not by_slip.get(slip.name):
            warnings.append(f"Salary Slip {slip.name} has no immutable VN payroll evidence.")
        if slip.vn_payroll_compliance_status != "Ready":
            warnings.append(f"Salary Slip {slip.name} VN payroll status is {slip.vn_payroll_compliance_status or 'Missing'}.")
    return [dict(row) for row in slips], [dict(row) for row in evidence], warnings


def build_05_kk_tncn(company: str, from_date, to_date) -> dict:
    from_date, to_date = getdate(from_date), getdate(to_date)
    slips, evidence, warnings = _submitted_payroll(company, from_date, to_date)
    aggregate = aggregate_pit_evidence(evidence)
    totals = select_pit_totals(aggregate)
    return {
        "form_code": "05/KK-TNCN",
        "schema_version": "canonical-v1",
        "company": company,
        "period": {"from_date": str(from_date), "to_date": str(to_date)},
        "calculation_basis": "Submitted HRMS Salary Slips + immutable VN payroll evidence",
        "summary": {
            "employee_count": aggregate["employee_count"],
            "salary_slip_count": aggregate["salary_slip_count"],
            **totals,
        },
        "employees": aggregate["employees"],
        "source_salary_slips": slips,
        "snapshot_hashes": aggregate["snapshot_hashes"],
        "warnings": sorted(set(warnings)),
        "adapter_ready": False,
        "review_required": True,
        "scope_note": "Canonical withholding model only; official form indicators/annexes remain adapter-versioned.",
    }


def build_05_qtt_tncn(company: str, from_date, to_date) -> dict:
    payload = build_05_kk_tncn(company, from_date, to_date)
    payload["form_code"] = "05/QTT-TNCN"
    payload["scope_note"] = "Canonical annual finalization evidence model; authorization and official annex mapping require explicit review in the format adapter."
    return payload
