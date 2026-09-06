from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

import frappe
from frappe.utils import getdate

BHXH_SOURCE_URL = "https://baohiemxahoi.gov.vn/thu-tuc-hanh-chinh/pages/default.aspx?ItemID=71"
BHXH_FORM_HASHES = {
    "TK1_TS": "629efd6340e2baef003dd4a7069f287140abda468a8d6a8aa9f69dd56e6ef225",
    "TK3_TS": "f045e830adb50555529e0a17eb4ddcf39c1e6da54e1098abd4ba25c3309220bd",
    "D02_LT": "29ce038a9de1a04cfd7b75f26bd5366bb04282f3bb16b70dcd781f0c39850a0d",
}


def _safe_values(doctype: str, name: str, fields: list[str]) -> dict:
    meta = frappe.get_meta(doctype)
    selected = [field for field in fields if field == "name" or meta.has_field(field)]
    row = frappe.db.get_value(doctype, name, selected, as_dict=True) or {}
    return dict(row)


def _active_social_profile(employee: str, when):
    when = getdate(when)
    rows = frappe.get_all(
        "VN Social Insurance Profile",
        filters={"employee": employee, "effective_from": ["<=", when]},
        fields=["name", "social_insurance_number", "participate_bhxh", "participate_bhyt", "participate_bhtn", "participate_oai", "wage_region", "contribution_category", "effective_from", "effective_to", "rule_set"],
        order_by="effective_from desc",
    )
    rows = [row for row in rows if not row.effective_to or getdate(row.effective_to) >= when]
    return dict(rows[0]) if rows else None


def build_tk1_ts(employee: str, as_of_date) -> dict:
    when = getdate(as_of_date)
    employee_row = _safe_values("Employee", employee, [
        "name", "employee_name", "gender", "date_of_birth", "company", "personal_email",
        "cell_number", "current_address", "permanent_address", "passport_number",
    ])
    if not employee_row:
        frappe.throw(f"Unknown Employee: {employee}")
    profile = _active_social_profile(employee, when)
    warnings = []
    if not profile:
        warnings.append("No active VN Social Insurance Profile exists for the employee on the requested date.")
    return {
        "form_code": "TK1-TS",
        "schema_version": "canonical-v1",
        "as_of_date": str(when),
        "employee": employee_row,
        "social_insurance_profile": profile,
        "source_reference": "BHXH administrative procedure ItemID=71",
        "source_url": BHXH_SOURCE_URL,
        "source_sha256": BHXH_FORM_HASHES["TK1_TS"],
        "warnings": warnings,
        "adapter_ready": False,
        "review_required": True,
    }


def build_tk3_ts(company: str, as_of_date) -> dict:
    when = getdate(as_of_date)
    company_row = _safe_values("Company", company, [
        "name", "company_name", "abbr", "tax_id", "phone_no", "email", "website",
        "registration_details", "country", "default_currency",
    ])
    if not company_row:
        frappe.throw(f"Unknown Company: {company}")
    return {
        "form_code": "TK3-TS",
        "schema_version": "canonical-v1",
        "as_of_date": str(when),
        "company": company_row,
        "source_reference": "BHXH administrative procedure ItemID=71",
        "source_url": BHXH_SOURCE_URL,
        "source_sha256": BHXH_FORM_HASHES["TK3_TS"],
        "warnings": [],
        "adapter_ready": False,
        "review_required": True,
    }


def build_d02_lt(company: str, from_date, to_date) -> dict:
    from_date, to_date = getdate(from_date), getdate(to_date)
    company_master = _safe_values("Company", company, [
        "name", "company_name", "tax_id", "phone_no", "email", "registration_details", "country", "default_currency",
    ])
    slips = frappe.get_all(
        "Salary Slip",
        filters={"company": company, "docstatus": 1, "end_date": ["between", [from_date, to_date]]},
        fields=["name", "employee", "employee_name", "end_date", "vn_payroll_snapshot_hash", "vn_payroll_compliance_status"],
        order_by="employee asc, end_date asc, name asc",
        limit_page_length=0,
    )
    names = [row.name for row in slips]
    evidence = []
    if names:
        evidence = frappe.get_all(
            "VN Payroll Calculation Line",
            filters={"salary_slip": ["in", names], "line_type": ["in", ["BHXH_EE", "BHYT_EE", "BHTN_EE", "BHXH_ER", "BHYT_ER", "BHTN_ER", "OAI_ER"]]},
            fields=["salary_slip", "employee", "line_type", "base_amount", "amount", "snapshot_hash", "rule_set"],
            order_by="employee asc, salary_slip asc, line_type asc",
            limit_page_length=0,
        )
    by_slip = defaultdict(dict)
    for row in evidence:
        by_slip[row.salary_slip][row.line_type] = dict(row)
    rows = []
    warnings = []
    for slip in slips:
        lines = by_slip.get(slip.name, {})
        if not lines:
            warnings.append(f"Salary Slip {slip.name} has no social-insurance evidence.")
        employee_master = _safe_values("Employee", slip.employee, [
            "name", "employee_name", "gender", "date_of_birth", "passport_number",
            "designation", "employment_type", "department", "date_of_joining", "contract_end_date",
            "current_address", "permanent_address", "cell_number", "personal_email",
        ])
        social_profile = _active_social_profile(slip.employee, slip.end_date)
        rows.append({
            "employee": slip.employee,
            "employee_name": slip.employee_name,
            "employee_master": employee_master,
            "social_insurance_profile": social_profile,
            "salary_slip": slip.name,
            "period_end": str(slip.end_date),
            "snapshot_hash": slip.vn_payroll_snapshot_hash,
            "compliance_status": slip.vn_payroll_compliance_status,
            "bhxh_base": Decimal(str((lines.get("BHXH_EE") or lines.get("BHXH_ER") or {}).get("base_amount") or 0)),
            "bhyt_base": Decimal(str((lines.get("BHYT_EE") or lines.get("BHYT_ER") or {}).get("base_amount") or 0)),
            "bhtn_base": Decimal(str((lines.get("BHTN_EE") or lines.get("BHTN_ER") or {}).get("base_amount") or 0)),
            "employee_bhxh": Decimal(str((lines.get("BHXH_EE") or {}).get("amount") or 0)),
            "employee_bhyt": Decimal(str((lines.get("BHYT_EE") or {}).get("amount") or 0)),
            "employee_bhtn": Decimal(str((lines.get("BHTN_EE") or {}).get("amount") or 0)),
            "employer_bhxh": Decimal(str((lines.get("BHXH_ER") or {}).get("amount") or 0)),
            "employer_bhyt": Decimal(str((lines.get("BHYT_ER") or {}).get("amount") or 0)),
            "employer_bhtn": Decimal(str((lines.get("BHTN_ER") or {}).get("amount") or 0)),
            "employer_oai": Decimal(str((lines.get("OAI_ER") or {}).get("amount") or 0)),
        })
    return {
        "form_code": "D02-LT",
        "schema_version": "canonical-v1",
        "company": company,
        "company_master": company_master,
        "period": {"from_date": str(from_date), "to_date": str(to_date)},
        "rows": rows,
        "source_reference": "BHXH administrative procedure ItemID=71",
        "source_url": BHXH_SOURCE_URL,
        "source_sha256": BHXH_FORM_HASHES["D02_LT"],
        "warnings": sorted(set(warnings)),
        "adapter_ready": False,
        "review_required": True,
    }
