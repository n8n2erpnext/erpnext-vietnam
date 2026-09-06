from __future__ import annotations

import frappe
from frappe import _


def _count(doctype: str, filters: dict | None = None) -> int:
    if not frappe.db.exists("DocType", doctype):
        return 0
    return int(frappe.db.count(doctype, filters or {}))


def _production_endpoint_health(company: str) -> list[dict]:
    if not frappe.db.exists("DocType", "VN Integration Endpoint"):
        return []
    rows = frappe.get_all(
        "VN Integration Endpoint",
        filters={"company": company, "environment": "PRODUCTION", "enabled": 1},
        fields=["name", "endpoint_name", "adapter", "adapter_certification_version", "adapter_certification_hash"],
        order_by="endpoint_name asc",
    )
    result = []
    for row in rows:
        status = "PINNED" if row.adapter_certification_version and row.adapter_certification_hash else "MISSING_CERTIFICATION_PIN"
        result.append({
            "name": row.name,
            "endpoint_name": row.endpoint_name,
            "adapter": row.adapter,
            "certification_version": row.adapter_certification_version,
            "certification_hash": row.adapter_certification_hash,
            "status": status,
        })
    return result


def build_company_health(company: str) -> dict:
    if not company or not frappe.db.exists("Company", company):
        frappe.throw(_("A valid Company is required."))

    settings_name = frappe.db.get_value("VN Localization Settings", {"company": company}, "name")
    settings = frappe.get_doc("VN Localization Settings", settings_name) if settings_name else None
    installed_apps = set(frappe.get_installed_apps())
    hrms_installed = "hrms" in installed_apps
    coa_mapping_count = _count("VN COA Mapping", {"company": company})
    einvoice_profile_count = _count("VN E-Invoice Profile", {"company": company})
    enabled_endpoint_count = _count("VN Integration Endpoint", {"company": company, "enabled": 1})
    production_endpoints = _production_endpoint_health(company)

    warnings: list[dict] = []
    if not settings:
        warnings.append({"level": "ERROR", "code": "SETUP_MISSING", "message": _("Vietnam Localization Setup has not been applied for this Company.")})
    else:
        if settings.enable_payroll_compliance and not hrms_installed:
            warnings.append({"level": "ERROR", "code": "HRMS_MISSING", "message": _("PIT payroll compliance is enabled but HRMS is not installed.")})
        if settings.enable_social_insurance and not hrms_installed:
            warnings.append({"level": "ERROR", "code": "HRMS_MISSING_SOCIAL", "message": _("Social-insurance compliance is enabled but HRMS is not installed.")})
        if settings.enable_einvoice and einvoice_profile_count == 0:
            warnings.append({"level": "WARNING", "code": "EINVOICE_PROFILE_MISSING", "message": _("E-invoice preparation is enabled but no VN E-Invoice Profile exists yet.")})
        if settings.enable_compliance_gateway and enabled_endpoint_count == 0:
            warnings.append({"level": "ERROR", "code": "GATEWAY_ENDPOINT_MISSING", "message": _("Compliance Gateway is enabled but no integration endpoint is enabled.")})
        if coa_mapping_count == 0:
            warnings.append({"level": "WARNING", "code": "COA_MAPPING_EMPTY", "message": _("No VN COA Mapping exists yet; statutory GL reconciliation may be incomplete.")})
    for endpoint in production_endpoints:
        if endpoint["status"] != "PINNED":
            warnings.append({"level": "ERROR", "code": "PRODUCTION_CERTIFICATION_MISSING", "message": _("A production integration endpoint is missing its adapter certification pin."), "endpoint": endpoint["name"]})

    has_error = any(item["level"] == "ERROR" for item in warnings)
    overall = "NOT_CONFIGURED" if not settings else ("NEEDS_ATTENTION" if has_error else ("READY_WITH_WARNINGS" if warnings else "READY"))
    setup = None
    if settings:
        setup = {
            "business_profile": settings.business_profile,
            "accounting_regime": settings.accounting_regime,
            "vat_method": settings.vat_method,
            "vat_validation_mode": settings.vat_validation_mode,
            "enable_payroll_compliance": bool(settings.enable_payroll_compliance),
            "enable_social_insurance": bool(settings.enable_social_insurance),
            "enable_einvoice": bool(settings.enable_einvoice),
            "enable_compliance_gateway": bool(settings.enable_compliance_gateway),
            "setup_version": settings.setup_version,
            "setup_snapshot_hash": settings.setup_snapshot_hash,
            "setup_applied_on": settings.setup_applied_on,
        }
    return {
        "company": company,
        "overall_status": overall,
        "setup": setup,
        "hrms_installed": hrms_installed,
        "counts": {
            "coa_mappings": coa_mapping_count,
            "einvoice_profiles": einvoice_profile_count,
            "enabled_integration_endpoints": enabled_endpoint_count,
            "production_endpoints": len(production_endpoints),
            "tax_declarations": _count("VN Tax Declaration", {"company": company}),
            "social_insurance_exports": _count("VN Social Insurance Export", {"company": company}),
            "einvoices": _count("VN E-Invoice", {"company": company}),
            "submissions": _count("VN Submission", {"company": company}),
        },
        "production_endpoints": production_endpoints,
        "warnings": warnings,
        "read_only": True,
    }


@frappe.whitelist()
def get_health(company: str):
    if not frappe.has_permission("Company", ptype="read", doc=company):
        frappe.throw(_("Not permitted to view Vietnam localization health for this Company."), frappe.PermissionError)
    return build_company_health(company)
