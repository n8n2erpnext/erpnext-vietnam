from __future__ import annotations

import hashlib
import importlib
import json
from typing import Any

import frappe

from erpnext_vietnam.diagnostics.compatibility import SUPPORTED_MAJORS, is_supported
from erpnext_vietnam.setup.domain_profiles import get_domain_profile_options

CRITICAL_DOCTYPES = (
    "VN Localization Settings", "VN Business Profile", "VN Legal Instrument", "VN Rule Set", "VN Rate Rule",
    "VN Statutory Account", "VN COA Mapping", "VN VAT Classification", "VN VAT Reporting Category",
    "VN Tax Declaration", "VN Social Insurance Export", "VN E-Invoice Profile", "VN E-Invoice",
    "VN Integration Endpoint", "VN Submission", "VN Submission Attempt",
)
CRITICAL_PAGES = ("vn-setup-wizard", "vn-localization-health")


def _version(app: str) -> str | None:
    try:
        module = importlib.import_module(app)
    except Exception:
        return None
    return str(getattr(module, "__version__", "") or "") or None


def _check(code: str, ok: bool, message: str, *, level: str = "ERROR", detail: Any = None) -> dict:
    return {"code": code, "ok": bool(ok), "level": "PASS" if ok else level, "message": message, "detail": detail}


def _snapshot_hash_ok(name: str) -> bool:
    doc = frappe.get_doc("VN Localization Settings", name)
    if not doc.setup_snapshot_json or not doc.setup_snapshot_hash:
        return False
    try:
        payload = json.loads(doc.setup_snapshot_json)
    except json.JSONDecodeError:
        return False
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest() == doc.setup_snapshot_hash


def run() -> dict:
    installed = set(frappe.get_installed_apps())
    checks: list[dict] = []
    versions = {app: _version(app) for app in ("frappe", "erpnext", "hrms", "erpnext_vietnam") if app in installed or app == "erpnext_vietnam"}

    for app in ("frappe", "erpnext"):
        present = app in installed
        checks.append(_check(f"APP_{app.upper()}_INSTALLED", present, f"{app} is installed" if present else f"{app} is required but not installed"))
        if present:
            checks.append(_check(f"APP_{app.upper()}_MAJOR", is_supported(app, versions.get(app)), f"{app} {versions.get(app)} is within supported major(s) {sorted(SUPPORTED_MAJORS[app])}", detail=versions.get(app)))
    if "hrms" in installed:
        checks.append(_check("APP_HRMS_MAJOR", is_supported("hrms", versions.get("hrms")), f"Optional HRMS {versions.get('hrms')} is within supported major(s) {sorted(SUPPORTED_MAJORS['hrms'])}", detail=versions.get("hrms")))
    else:
        checks.append(_check("APP_HRMS_OPTIONAL", True, "HRMS is not installed; payroll/social-insurance features must remain unused", level="WARNING"))

    for doctype in CRITICAL_DOCTYPES:
        exists = bool(frappe.db.exists("DocType", doctype))
        checks.append(_check("DOCTYPE_" + doctype.upper().replace(" ", "_"), exists, f"Required DocType {doctype} is available" if exists else f"Required DocType {doctype} is missing"))
    for page in CRITICAL_PAGES:
        exists = bool(frappe.db.exists("Page", page))
        checks.append(_check("PAGE_" + page.upper().replace("-", "_"), exists, f"Required Desk page {page} is available" if exists else f"Required Desk page {page} is missing"))

    expected_profiles = {row["code"] for row in get_domain_profile_options()}
    seeded_profiles = set(frappe.get_all("VN Business Profile", pluck="name")) if frappe.db.exists("DocType", "VN Business Profile") else set()
    missing_profiles = sorted(expected_profiles - seeded_profiles)
    checks.append(_check("BUSINESS_PROFILE_SEEDS", not missing_profiles, "Business-profile seed registry is complete" if not missing_profiles else "Business-profile seed registry is incomplete", detail={"expected": len(expected_profiles), "seeded": len(seeded_profiles), "missing": missing_profiles}))

    bad_snapshots = []
    if frappe.db.exists("DocType", "VN Localization Settings"):
        for name in frappe.get_all("VN Localization Settings", pluck="name"):
            if not _snapshot_hash_ok(name):
                bad_snapshots.append(name)
    checks.append(_check("SETUP_SNAPSHOT_INTEGRITY", not bad_snapshots, "All applied setup snapshots match their SHA-256" if not bad_snapshots else "One or more setup snapshots failed SHA-256 verification", detail=bad_snapshots))

    bad_sandbox_prod = []
    missing_pins = []
    if frappe.db.exists("DocType", "VN Integration Endpoint"):
        prod = frappe.get_all("VN Integration Endpoint", filters={"environment": "PRODUCTION", "enabled": 1}, fields=["name", "adapter", "adapter_certification_version", "adapter_certification_hash"])
        for row in prod:
            if str(row.adapter or "").startswith("sandbox."):
                bad_sandbox_prod.append(row.name)
            if not row.adapter_certification_version or not row.adapter_certification_hash:
                missing_pins.append(row.name)
    checks.append(_check("NO_SANDBOX_PRODUCTION_ENDPOINT", not bad_sandbox_prod, "No enabled production endpoint uses a sandbox adapter" if not bad_sandbox_prod else "Enabled production endpoint uses a sandbox adapter", detail=bad_sandbox_prod))
    checks.append(_check("PRODUCTION_CERTIFICATION_PINS", not missing_pins, "All enabled production endpoints have certification pins" if not missing_pins else "One or more enabled production endpoints lack certification pins", detail=missing_pins))

    failures = [item for item in checks if not item["ok"] and item["level"] == "ERROR"]
    warnings = [item for item in checks if not item["ok"] and item["level"] == "WARNING"]
    return {
        "status": "FAIL" if failures else ("WARN" if warnings else "PASS"),
        "versions": versions,
        "checks": checks,
        "failure_count": len(failures),
        "warning_count": len(warnings),
        "read_only": True,
    }


@frappe.whitelist()
def doctor():
    if not frappe.has_permission("System Settings", ptype="read"):
        frappe.throw("System Manager permission is required to run ERPNext Vietnam release doctor", frappe.PermissionError)
    return run()
