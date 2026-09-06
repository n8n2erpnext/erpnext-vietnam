from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal

import frappe
from frappe.utils import getdate

from erpnext_vietnam.accounting.roles import VAT_INPUT_ROLE, VAT_OUTPUT_ROLE
from erpnext_vietnam.accounting.service import resolve_coa_mapping
from erpnext_vietnam.declarations.math import aggregate_pit_evidence, select_pit_totals
from erpnext_vietnam.declarations.vat_reporting import resolve_reporting_category
from erpnext_vietnam.vat.reconciliation import build_vat_reconciliation


def _settings(company: str):
    name = frappe.db.get_value("VN Localization Settings", {"company": company}, "name")
    return frappe.get_doc("VN Localization Settings", name) if name else None


def _native_vat_detail_by_item(doc, vat_account: str | None) -> dict[str, dict]:
    result = defaultdict(lambda: {"taxable_amount": Decimal("0"), "tax_amount": Decimal("0"), "detail_count": 0})
    if not vat_account:
        return result
    tax_rows = {row.name: row for row in doc.taxes}
    for detail in getattr(doc, "item_wise_tax_details", []) or []:
        tax_row = tax_rows.get(detail.tax_row)
        if not tax_row or tax_row.account_head != vat_account:
            continue
        bucket = result[detail.item_row]
        bucket["taxable_amount"] += Decimal(str(detail.taxable_amount or 0))
        bucket["tax_amount"] += Decimal(str(detail.amount or 0))
        bucket["detail_count"] += 1
    return result


def _submitted_invoices(company: str, from_date, to_date) -> tuple[list[dict], list[dict], list[str]]:
    sources: list[dict] = []
    reporting_lines: list[dict] = []
    warnings: list[str] = []
    settings = _settings(company)
    company_currency = frappe.db.get_value("Company", company, "default_currency")

    for doctype, direction, role in (
        ("Sales Invoice", "Output", VAT_OUTPUT_ROLE),
        ("Purchase Invoice", "Input", VAT_INPUT_ROLE),
    ):
        rows = frappe.get_all(
            doctype,
            filters={"company": company, "docstatus": 1, "posting_date": ["between", [from_date, to_date]]},
            fields=["name", "posting_date", "vn_vat_snapshot_hash", "vn_vat_validation_status"],
            order_by="posting_date asc, name asc",
            limit_page_length=0,
        )
        for row in rows:
            source = {
                "doctype": doctype,
                "name": row.name,
                "date": str(row.posting_date),
                "snapshot_hash": row.vn_vat_snapshot_hash,
                "validation_status": row.vn_vat_validation_status,
            }
            sources.append(source)
            doc = frappe.get_doc(doctype, row.name)
            vat_account = None
            if settings:
                mapping = resolve_coa_mapping(company, role, getdate(row.posting_date), settings.accounting_regime)
                vat_account = mapping.account if mapping else None
            if not vat_account:
                warnings.append(f"{doctype} {row.name}: no effective VAT control-account mapping for exact item-wise tax evidence.")
            native = _native_vat_detail_by_item(doc, vat_account)

            for item in doc.items:
                reporting_name = getattr(item, "vn_vat_reporting_category", None)
                reporting = None
                reporting_error = None
                if reporting_name:
                    try:
                        reporting = resolve_reporting_category(
                            reporting_name, direction, row.posting_date, getattr(item, "vn_vat_treatment", None)
                        )
                    except frappe.ValidationError as exc:
                        reporting_error = str(exc)
                        warnings.append(f"{doctype} {row.name} row {item.idx}: {reporting_error}")

                detail = native.get(item.name) or {}
                has_native_tax = bool(detail.get("detail_count"))
                explicit_rate = getattr(item, "vn_vat_rate", None)
                exact_zero_tax = explicit_rate not in (None, "") and Decimal(str(explicit_rate)) == 0
                tax_amount = detail.get("tax_amount") if has_native_tax else (Decimal("0") if exact_zero_tax else None)
                taxable_amount = detail.get("taxable_amount") if has_native_tax else None
                base_net_value = Decimal(str(getattr(item, "base_net_amount", 0) or 0))
                if direction == "Output" and reporting and reporting.get("tax_indicator") and taxable_amount is not None:
                    value = Decimal(str(taxable_amount))
                    value_basis = "ERPNext Item Wise Tax Detail taxable_amount"
                else:
                    value = base_net_value
                    value_basis = "ERPNext invoice item base_net_amount"
                stored_reporting_hash = getattr(item, "vn_vat_reporting_snapshot_hash", None)
                reporting_hash_matches = bool(
                    reporting and stored_reporting_hash and stored_reporting_hash == reporting.get("snapshot_hash")
                )
                if reporting and not stored_reporting_hash:
                    warnings.append(f"{doctype} {row.name} row {item.idx}: reporting category exists but no immutable reporting snapshot hash is stored.")
                elif reporting and stored_reporting_hash and not reporting_hash_matches:
                    warnings.append(f"{doctype} {row.name} row {item.idx}: stored reporting snapshot hash does not match the released category definition.")

                line = {
                    "doctype": doctype,
                    "parent": row.name,
                    "idx": item.idx,
                    "item_row": item.name,
                    "item_code": item.item_code,
                    "posting_date": str(row.posting_date),
                    "company_currency": company_currency,
                    "reporting_value": value,
                    "reporting_value_basis": value_basis,
                    "native_taxable_amount": taxable_amount,
                    "tax_amount": tax_amount,
                    "native_tax_detail_count": int(detail.get("detail_count") or 0),
                    "vat_treatment": getattr(item, "vn_vat_treatment", None),
                    "vat_rate": getattr(item, "vn_vat_rate", None),
                    "vat_snapshot_hash": getattr(item, "vn_vat_snapshot_hash", None),
                    "reporting_category_name": reporting_name,
                    "reporting_category": reporting,
                    "reporting_snapshot_hash": stored_reporting_hash,
                    "reporting_snapshot_hash_matches": reporting_hash_matches,
                    "reporting_error": reporting_error,
                }
                if doctype == "Purchase Invoice":
                    line.update({
                        "input_vat_deduction_status": getattr(item, "vn_input_vat_deduction_status", None),
                        "input_vat_deductible_ratio": getattr(item, "vn_input_vat_deductible_ratio", None),
                        "input_vat_evidence_reference": getattr(item, "vn_input_vat_evidence_reference", None),
                    })
                reporting_lines.append(line)
    return sources, reporting_lines, sorted(set(warnings))


def build_01_gtgt(company: str, from_date, to_date) -> dict:
    from_date, to_date = getdate(from_date), getdate(to_date)
    reconciliation = build_vat_reconciliation(company, from_date, to_date)
    sources, reporting_lines, reporting_warnings = _submitted_invoices(company, from_date, to_date)
    warnings = list(reconciliation.get("warnings") or []) + reporting_warnings
    if not reconciliation.get("configured"):
        warnings.append("Vietnam VAT localization is not configured for this Company.")
    missing = sum(1 for row in sources if not row.get("snapshot_hash"))
    if missing:
        warnings.append(f"{missing} submitted VAT source invoices do not carry a VN VAT snapshot hash.")
    return {
        "form_code": "01/GTGT",
        "schema_version": "canonical-v2",
        "company": company,
        "company_currency": frappe.db.get_value("Company", company, "default_currency"),
        "period": {"from_date": str(from_date), "to_date": str(to_date)},
        "calculation_basis": "ERPNext native GL + item-wise tax details + immutable VN VAT/reporting evidence",
        "accounting_summary": reconciliation.get("gl") or {},
        "invoice_coverage": reconciliation.get("invoice_coverage") or {},
        "input_vat_evidence": reconciliation.get("purchase_input_evidence") or {},
        "source_documents": sources,
        "reporting_lines": reporting_lines,
        "warnings": sorted(set(warnings)),
        "adapter_ready": False,
        "review_required": True,
        "scope_note": "Canonical evidence only; TT89 indicator mapping is versioned separately and refuses missing categories/evidence.",
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
