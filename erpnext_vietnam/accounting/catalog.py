from __future__ import annotations

import re
import unicodedata

import frappe
from frappe import _

from erpnext_vietnam.accounting.catalog_data import load_tt99_catalog, validate_catalog
from erpnext_vietnam.accounting.roles import STATUTORY_ROLES, validate_statutory_role

def _record_key(catalog_version: str, account_code: str) -> str:
    return f"{catalog_version}::{account_code}"


def seed_tt99_statutory_accounts() -> int:
    data = load_tt99_catalog()
    validate_catalog(data)
    inserted = 0
    for row in data["records"]:
        key = _record_key(data["catalog_version"], row["account_code"])
        if frappe.db.exists("VN Statutory Account", key):
            continue
        frappe.get_doc({
            "doctype": "VN Statutory Account",
            "record_key": key,
            "catalog_version": data["catalog_version"],
            "accounting_regime": data["accounting_regime"],
            "account_code": row["account_code"],
            "parent_code": row.get("parent_code"),
            "account_name_vi": row["account_name_vi"],
            "account_level": row["level"],
            "account_category": row["category"],
            "effective_from": data["effective_from"],
            "legal_instrument": data["legal_instrument"],
            "source_printed_page": row["source_printed_page"],
            "source_sha256": data["source_sha256"],
            "reference_status": "Released",
        }).insert(ignore_permissions=True)
        inserted += 1
    return inserted


def _normalize_name(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch)).lower()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


@frappe.whitelist()
def preview_company_mapping(company: str, accounting_regime: str = "TT99_2025"):
    """Read-only mapping suggestions; never creates or renames ERPNext Accounts."""
    if not frappe.db.exists("Company", company):
        frappe.throw(_("Company {0} does not exist").format(company))
    if accounting_regime != "TT99_2025":
        frappe.throw(_("P1B mapping preview currently supports TT99_2025 only."))

    catalog = load_tt99_catalog()
    by_code = {row["account_code"]: row for row in catalog["records"]}
    accounts = frappe.get_all(
        "Account",
        filters={"company": company, "is_group": 0},
        fields=["name", "account_name", "account_number", "root_type", "account_type"],
    )
    by_number = {str(a.account_number).strip(): a for a in accounts if a.account_number}
    by_name = {_normalize_name(a.account_name): a for a in accounts if a.account_name}
    suggestions = []
    for role, statutory_code in STATUTORY_ROLES.items():
        validate_statutory_role(role)
        statutory = by_code.get(statutory_code)
        if not statutory:
            continue
        existing = frappe.db.get_value(
            "VN COA Mapping",
            {"company": company, "statutory_role": role, "accounting_regime": accounting_regime},
            ["name", "account"],
            as_dict=True,
        )
        candidate = by_number.get(statutory_code)
        match_type = "EXACT_ACCOUNT_NUMBER" if candidate else None
        confidence = 1.0 if candidate else 0.0
        if not candidate:
            candidate = by_name.get(_normalize_name(statutory["account_name_vi"]))
            if candidate:
                match_type = "EXACT_NORMALIZED_NAME"
                confidence = 0.9
        suggestions.append({
            "statutory_role": role,
            "statutory_code": statutory_code,
            "statutory_name_vi": statutory["account_name_vi"],
            "existing_mapping": existing,
            "suggested_account": candidate.name if candidate else None,
            "match_type": match_type or "NO_MATCH",
            "confidence": confidence,
        })
    return {
        "company": company,
        "accounting_regime": accounting_regime,
        "catalog_version": catalog["catalog_version"],
        "source_sha256": catalog["source_sha256"],
        "read_only": True,
        "suggestions": suggestions,
    }
