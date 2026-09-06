from __future__ import annotations

import frappe
from frappe import _

from erpnext_vietnam.payroll.reconciliation import get_payroll_reconciliation


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.company or not filters.from_date or not filters.to_date:
        frappe.throw(_("Company, From Date and To Date are required."))
    results = get_payroll_reconciliation(filters.company, filters.from_date, filters.to_date, filters.employee)
    currency = frappe.db.get_value("Company", filters.company, "default_currency")
    rows = []
    for result in results:
        detail = " | ".join(result.get("warnings") or [])
        rows.append({
            "salary_slip": result.get("salary_slip"), "employee": result.get("employee"),
            "posting_date": result.get("posting_date"), "status": result.get("status"),
            "employee_expected": result.get("employee_expected_total", 0),
            "employee_actual": result.get("employee_actual_total", 0),
            "employee_variance": result.get("employee_variance_total", 0),
            "employer_expected": result.get("employer_expected_total", 0),
            "snapshot_hash": result.get("snapshot_hash"), "detail": detail, "currency": currency,
        })
    columns = [
        {"label": _("Salary Slip"), "fieldname": "salary_slip", "fieldtype": "Link", "options": "Salary Slip", "width": 180},
        {"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 180},
        {"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
        {"label": _("Employee Expected"), "fieldname": "employee_expected", "fieldtype": "Currency", "options": "currency", "width": 150},
        {"label": _("Employee Actual"), "fieldname": "employee_actual", "fieldtype": "Currency", "options": "currency", "width": 150},
        {"label": _("Variance"), "fieldname": "employee_variance", "fieldtype": "Currency", "options": "currency", "width": 130},
        {"label": _("Employer Expected"), "fieldname": "employer_expected", "fieldtype": "Currency", "options": "currency", "width": 150},
        {"label": _("Snapshot Hash"), "fieldname": "snapshot_hash", "fieldtype": "Data", "width": 160},
        {"label": _("Detail"), "fieldname": "detail", "fieldtype": "Data", "width": 320},
        {"label": _("Currency"), "fieldname": "currency", "fieldtype": "Data", "hidden": 1},
    ]
    return columns, rows
