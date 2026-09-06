from __future__ import annotations

import hashlib
import json

import frappe
from frappe import _
from frappe.utils import now_datetime

from erpnext_vietnam.setup.domain_profiles import get_domain_profile, get_domain_profile_options as _profile_options


@frappe.whitelist()
def get_domain_profile_options():
    return _profile_options()


def get_setup_stages(args=None):
    args = frappe._dict(args or {})
    return [
        {
            "status": _("Preparing Vietnam localization"),
            "fail_msg": _("Failed to prepare Vietnam localization"),
            "tasks": [{"fn": sync_business_profiles, "args": args}],
        },
        {
            "status": _("Applying Vietnam localization profile"),
            "fail_msg": _("Failed to apply Vietnam localization profile"),
            "tasks": [{"fn": apply_localization_profile, "args": args}],
        },
    ]


def sync_business_profiles(args=None):
    for profile in _profile_options():
        if frappe.db.exists("VN Business Profile", profile["code"]):
            continue
        doc = frappe.get_doc(
            {
                "doctype": "VN Business Profile",
                "profile_code": profile["code"],
                "title": profile["title"],
                "description": profile["description"],
                "suggested_modules_json": json.dumps(profile["suggested_modules"], ensure_ascii=False),
                "enabled": 1,
                "profile_version": "1",
            }
        )
        doc.insert(ignore_permissions=True)


def _resolve_company(args):
    company = args.get("company") or args.get("company_name") or frappe.defaults.get_user_default("Company")
    if company and frappe.db.exists("Company", company):
        return company
    if args.get("company_name"):
        found = frappe.db.get_value("Company", {"company_name": args.company_name}, "name")
        if found:
            return found
    return None


def build_setup_snapshot(args, company: str) -> dict[str, object]:
    profile = get_domain_profile(args.get("vn_business_profile") or "OTHER")
    return {
        "schema_version": 1,
        "company": company,
        "business_profile": profile.code,
        "accounting_regime": args.get("vn_accounting_regime") or "TT99_2025",
        "vat_method": args.get("vn_vat_method") or "DEDUCTION",
        "enable_payroll_compliance": bool(int(args.get("vn_enable_payroll_compliance") or 0)),
        "enable_social_insurance": bool(int(args.get("vn_enable_social_insurance") or 0)),
        "enable_einvoice": bool(int(args.get("vn_enable_einvoice") or 0)),
        "enable_compliance_gateway": False,
        "profile_version": "1",
    }


def apply_localization_profile(args):
    args = frappe._dict(args or {})
    company = _resolve_company(args)
    if not company:
        frappe.throw(_("A valid Company is required to configure ERPNext Vietnam."))

    snapshot = build_setup_snapshot(args, company)
    payload = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    name = frappe.db.get_value("VN Localization Settings", {"company": company}, "name")
    doc = frappe.get_doc("VN Localization Settings", name) if name else frappe.new_doc("VN Localization Settings")
    doc.company = company
    doc.business_profile = snapshot["business_profile"]
    doc.accounting_regime = snapshot["accounting_regime"]
    doc.vat_method = snapshot["vat_method"]
    doc.enable_payroll_compliance = snapshot["enable_payroll_compliance"]
    doc.enable_social_insurance = snapshot["enable_social_insurance"]
    doc.enable_einvoice = snapshot["enable_einvoice"]
    doc.enable_compliance_gateway = 0
    doc.setup_snapshot_json = payload
    doc.setup_snapshot_hash = digest
    doc.setup_applied_on = now_datetime()
    doc.setup_version = "1"
    doc.save(ignore_permissions=True)
