from __future__ import annotations

from datetime import date

import frappe
from frappe.utils import getdate

from erpnext_vietnam.accounting.roles import validate_statutory_role


class COAMappingConflictError(frappe.ValidationError):
    pass


def resolve_coa_mapping(company: str, statutory_role: str, when: date, accounting_regime: str | None = None):
    role = validate_statutory_role(statutory_role)
    when = getdate(when)
    filters = {"company": company, "statutory_role": role, "effective_from": ["<=", when]}
    if accounting_regime:
        filters["accounting_regime"] = accounting_regime
    rows = frappe.get_all(
        "VN COA Mapping",
        filters=filters,
        fields=["name", "account", "accounting_regime", "effective_from", "effective_to", "rule_set"],
        order_by="effective_from desc",
    )
    rows = [r for r in rows if not r.effective_to or getdate(r.effective_to) >= when]
    if not rows:
        return None
    best_date = getdate(rows[0].effective_from)
    tied = [r for r in rows if getdate(r.effective_from) == best_date]
    if len(tied) > 1:
        raise COAMappingConflictError(
            f"Ambiguous VN COA Mapping for {company} / {role} on {when}: {', '.join(r.name for r in tied)}"
        )
    return rows[0]
