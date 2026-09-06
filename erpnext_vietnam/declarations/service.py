from __future__ import annotations

import calendar
import json

import frappe
from frappe.utils import getdate, now_datetime

from erpnext_vietnam.declarations.adapters.bhxh_qd505_1040 import adapt_social_insurance_export
from erpnext_vietnam.declarations.adapters.tax_tt89 import adapt_tax_declaration
from erpnext_vietnam.declarations.bhxh import build_d02_lt, build_tk1_ts, build_tk3_ts
from erpnext_vietnam.declarations.canonical import canonical_json, payload_hash
from erpnext_vietnam.declarations.registry import BHXH_FORMS, TAX_FORMS
from erpnext_vietnam.declarations.tax import build_01_gtgt, build_05_kk_tncn, build_05_qtt_tncn


def _tax_payload(declaration_type: str, company: str, from_date, to_date):
    builders = {
        "01_GTGT": build_01_gtgt,
        "05_KK_TNCN": build_05_kk_tncn,
        "05_QTT_TNCN": build_05_qtt_tncn,
    }
    if declaration_type not in builders:
        frappe.throw(f"Unsupported VN tax declaration type: {declaration_type}")
    return builders[declaration_type](company, from_date, to_date)


def _evidence_snapshot(payload: dict) -> dict:
    excluded = {
        "adapter_ready", "review_required", "scope_note", "schema_version", "form_code",
        "statutory_inputs", "annual_annexes_reviewed", "statutory_rows",
    }
    return {key: value for key, value in payload.items() if key not in excluded}


def _parse_adapter_inputs(value) -> dict:
    if value in (None, ""):
        return {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            frappe.throw("Adapter Inputs must be valid JSON")
    if not isinstance(value, dict):
        frappe.throw("Adapter Inputs must be a JSON object")
    return value


def validate_tax_period(period_type: str, from_date, to_date):
    start, end = getdate(from_date), getdate(to_date)
    if start > end:
        frappe.throw("From Date cannot be after To Date")
    if period_type == "Month":
        expected_end = start.replace(day=calendar.monthrange(start.year, start.month)[1])
        if start.day != 1 or end != expected_end:
            frappe.throw("Month period must cover one full calendar month")
    elif period_type == "Quarter":
        if start.day != 1 or start.month not in (1, 4, 7, 10):
            frappe.throw("Quarter period must start on the first day of a calendar quarter")
        end_month = start.month + 2
        expected_end = start.replace(month=end_month, day=calendar.monthrange(start.year, end_month)[1])
        if end != expected_end:
            frappe.throw("Quarter period must cover one full calendar quarter")
    elif period_type == "Year":
        if start.month != 1 or start.day != 1 or end.year != start.year or end.month != 12 or end.day != 31:
            frappe.throw("Year period must cover one full calendar year")
    return start, end


def preview_tax_declaration(company: str, declaration_type: str, from_date, to_date, period_type: str, adapter_inputs=None):
    spec = TAX_FORMS.get(declaration_type)
    if not spec:
        frappe.throw(f"Unsupported VN tax declaration type: {declaration_type}")
    if period_type not in spec.period_types:
        frappe.throw(f"{spec.code} does not support period type {period_type}")
    from_date, to_date = validate_tax_period(period_type, from_date, to_date)
    payload = _tax_payload(declaration_type, company, from_date, to_date)
    inputs = _parse_adapter_inputs(adapter_inputs)
    if inputs:
        payload["statutory_inputs"] = inputs.get("indicators") or {}
        if declaration_type == "05_QTT_TNCN":
            payload["annual_annexes_reviewed"] = bool(inputs.get("annual_annexes_reviewed"))
    snapshot = _evidence_snapshot(payload)
    adapter = adapt_tax_declaration(payload)
    combined_warnings = sorted(set((payload.get("warnings") or []) + (adapter.get("warnings") or [])))
    return {
        "declaration_type": declaration_type,
        "form_code": spec.code,
        "period_type": period_type,
        "schema_version": payload.get("schema_version") or spec.schema_version,
        "calculation_snapshot": snapshot,
        "calculation_snapshot_hash": payload_hash(snapshot),
        "declaration": payload,
        "declaration_hash": payload_hash(payload),
        "adapter": adapter,
        "adapter_status": "Ready" if adapter.get("ready") else "Needs Review",
        "adapter_payload_hash": payload_hash(adapter),
        "warnings": combined_warnings,
        "read_only": True,
    }


@frappe.whitelist()
def get_tax_declaration_preview(company: str, declaration_type: str, from_date, to_date, period_type: str, adapter_inputs=None):
    if not frappe.has_permission("Company", ptype="read"):
        frappe.throw("Not permitted to read Company data", frappe.PermissionError)
    if declaration_type == "01_GTGT" and not frappe.has_permission("GL Entry", ptype="read"):
        frappe.throw("Not permitted to read accounting evidence", frappe.PermissionError)
    if declaration_type in {"05_KK_TNCN", "05_QTT_TNCN"} and not frappe.has_permission("Salary Slip", ptype="read"):
        frappe.throw("Not permitted to read payroll evidence", frappe.PermissionError)
    return preview_tax_declaration(company, declaration_type, from_date, to_date, period_type, adapter_inputs)


@frappe.whitelist()
def create_tax_declaration(company: str, declaration_type: str, from_date, to_date, period_type: str, adapter_inputs=None):
    if not frappe.has_permission("VN Tax Declaration", ptype="create"):
        frappe.throw("Not permitted to create VN Tax Declaration", frappe.PermissionError)
    preview = preview_tax_declaration(company, declaration_type, from_date, to_date, period_type, adapter_inputs)
    existing = frappe.db.get_value(
        "VN Tax Declaration",
        {
            "company": company,
            "declaration_type": declaration_type,
            "from_date": getdate(from_date),
            "to_date": getdate(to_date),
            "declaration_hash": preview["declaration_hash"],
            "status": ["!=", "Voided"],
        },
        "name",
    )
    if existing:
        return frappe.get_doc("VN Tax Declaration", existing).as_dict()
    doc = frappe.get_doc({
        "doctype": "VN Tax Declaration",
        "company": company,
        "declaration_type": declaration_type,
        "period_type": period_type,
        "from_date": getdate(from_date),
        "to_date": getdate(to_date),
        "status": "Prepared",
        "schema_version": preview["schema_version"],
        "legal_instrument": "89/2026/TT-BTC",
        "calculation_snapshot_json": canonical_json(preview["calculation_snapshot"]),
        "declaration_json": canonical_json(preview["declaration"]),
        "adapter_version": preview["adapter"].get("adapter_version"),
        "adapter_status": preview["adapter_status"],
        "adapter_payload_json": canonical_json(preview["adapter"]),
        "warning_json": canonical_json(preview["warnings"]),
        "prepared_at": now_datetime(),
    }).insert(ignore_permissions=True)
    return doc.as_dict()


def preview_social_insurance_export(export_type: str, company: str | None = None, employee: str | None = None, from_date=None, to_date=None, as_of_date=None, adapter_inputs=None):
    spec = BHXH_FORMS.get(export_type)
    if not spec:
        frappe.throw(f"Unsupported VN social-insurance export type: {export_type}")
    if export_type == "TK1_TS":
        if not employee or not as_of_date:
            frappe.throw("TK1-TS requires Employee and As Of Date")
        payload = build_tk1_ts(employee, as_of_date)
        subject_doctype, subject_name = "Employee", employee
        company = payload["employee"].get("company")
        from_date = to_date = getdate(as_of_date)
    elif export_type == "TK3_TS":
        if not company or not as_of_date:
            frappe.throw("TK3-TS requires Company and As Of Date")
        payload = build_tk3_ts(company, as_of_date)
        subject_doctype, subject_name = "Company", company
        from_date = to_date = getdate(as_of_date)
    else:
        if not company or not from_date or not to_date:
            frappe.throw("D02-LT requires Company, From Date and To Date")
        payload = build_d02_lt(company, from_date, to_date)
        subject_doctype, subject_name = None, None
        from_date, to_date = getdate(from_date), getdate(to_date)
    inputs = _parse_adapter_inputs(adapter_inputs)
    if inputs:
        payload["statutory_inputs"] = inputs
        if export_type == "D02_LT":
            payload["statutory_rows"] = inputs.get("rows") or []
    adapter = adapt_social_insurance_export(payload)
    combined_warnings = sorted(set((payload.get("warnings") or []) + (adapter.get("warnings") or [])))
    return {
        "export_type": export_type,
        "form_code": spec.code,
        "company": company,
        "subject_doctype": subject_doctype,
        "subject_name": subject_name,
        "from_date": from_date,
        "to_date": to_date,
        "schema_version": spec.schema_version,
        "payload": payload,
        "payload_hash": payload_hash(payload),
        "adapter": adapter,
        "adapter_status": "Ready" if adapter.get("ready") else "Needs Review",
        "adapter_payload_hash": payload_hash(adapter),
        "warnings": combined_warnings,
        "read_only": True,
    }


@frappe.whitelist()
def get_social_insurance_export_preview(export_type: str, company: str | None = None, employee: str | None = None, from_date=None, to_date=None, as_of_date=None, adapter_inputs=None):
    if export_type == "TK1_TS" and not frappe.has_permission("Employee", ptype="read"):
        frappe.throw("Not permitted to read Employee data", frappe.PermissionError)
    if export_type in {"TK3_TS", "D02_LT"} and not frappe.has_permission("Company", ptype="read"):
        frappe.throw("Not permitted to read Company data", frappe.PermissionError)
    if export_type == "D02_LT" and not frappe.has_permission("Salary Slip", ptype="read"):
        frappe.throw("Not permitted to read payroll evidence", frappe.PermissionError)
    return preview_social_insurance_export(export_type, company, employee, from_date, to_date, as_of_date, adapter_inputs)


@frappe.whitelist()
def create_social_insurance_export(export_type: str, company: str | None = None, employee: str | None = None, from_date=None, to_date=None, as_of_date=None, adapter_inputs=None):
    if not frappe.has_permission("VN Social Insurance Export", ptype="create"):
        frappe.throw("Not permitted to create VN Social Insurance Export", frappe.PermissionError)
    preview = preview_social_insurance_export(export_type, company, employee, from_date, to_date, as_of_date, adapter_inputs)
    existing = frappe.db.get_value(
        "VN Social Insurance Export",
        {
            "company": preview["company"],
            "export_type": export_type,
            "from_date": preview["from_date"],
            "to_date": preview["to_date"],
            "payload_hash": preview["payload_hash"],
            "status": ["!=", "Voided"],
        },
        "name",
    )
    if existing:
        return frappe.get_doc("VN Social Insurance Export", existing).as_dict()
    payload = preview["payload"]
    doc = frappe.get_doc({
        "doctype": "VN Social Insurance Export",
        "company": preview["company"],
        "export_type": export_type,
        "subject_doctype": preview["subject_doctype"],
        "subject_name": preview["subject_name"],
        "from_date": preview["from_date"],
        "to_date": preview["to_date"],
        "status": "Prepared",
        "schema_version": preview["schema_version"],
        "source_reference": payload.get("source_reference"),
        "source_url": payload.get("source_url"),
        "source_sha256": payload.get("source_sha256"),
        "canonical_payload_json": canonical_json(payload),
        "adapter_version": preview["adapter"].get("adapter_version"),
        "adapter_status": preview["adapter_status"],
        "adapter_payload_json": canonical_json(preview["adapter"]),
        "warning_json": canonical_json(preview["warnings"]),
        "prepared_at": now_datetime(),
    }).insert(ignore_permissions=True)
    return doc.as_dict()
