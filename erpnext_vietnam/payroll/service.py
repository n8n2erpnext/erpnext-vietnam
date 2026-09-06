from __future__ import annotations

import hashlib
import json
from decimal import Decimal

import frappe
from frappe.utils import getdate

from erpnext_vietnam.payroll.insurance_math import clamp_contribution_base, contribution_amount, d, money
from erpnext_vietnam.payroll.pit_math import nonresident_salary_tax, progressive_tax, resident_assessable_income


def _active_rows(doctype: str, filters: dict, when, fields: list[str], order_by="effective_from desc"):
    when = getdate(when)
    query = {**filters, "effective_from": ["<=", when]}
    rows = frappe.get_all(doctype, filters=query, fields=fields, order_by=order_by)
    return [row for row in rows if not row.get("effective_to") or getdate(row.effective_to) >= when]


def _single_active(doctype: str, filters: dict, when, fields: list[str]):
    rows = _active_rows(doctype, filters, when, fields)
    if not rows:
        return None
    best_date = getdate(rows[0].effective_from)
    tied = [row for row in rows if getdate(row.effective_from) == best_date]
    if len(tied) > 1:
        frappe.throw(f"Ambiguous {doctype} for {filters} on {getdate(when)}")
    return rows[0]


def _rate(code: str, when):
    row = _single_active(
        "VN Rate Rule", {"code": code, "rule_status": "Released"}, when,
        ["name", "code", "decimal_value", "unit", "effective_from", "effective_to", "rule_set", "legal_instrument", "legal_reference_detail"],
    )
    return row


def _settings(company: str):
    name = frappe.db.get_value("VN Localization Settings", {"company": company}, "name")
    return frappe.get_doc("VN Localization Settings", name) if name else None


def _component_meta(name: str):
    fields = [
        "vn_compliance_review_status", "vn_pit_taxable", "vn_pit_exemption_code", "vn_pit_taxable_ratio",
        "vn_bhxh_base_included", "vn_bhyt_base_included", "vn_bhtn_base_included", "vn_regular_stable_payment", "vn_legal_rule",
    ]
    return frappe.db.get_value("Salary Component", name, fields, as_dict=True) or frappe._dict()


def _active_dependents(employee: str, when) -> list:
    return _active_rows(
        "VN Dependent", {"employee": employee, "deduction_eligible": 1}, when,
        ["name", "dependent_name", "effective_from", "effective_to"], order_by="effective_from asc",
    )


def _pit_brackets(when):
    return _active_rows(
        "VN PIT Bracket", {"residency": "Resident", "period_basis": "Monthly", "rule_status": "Released"}, when,
        ["code", "sequence", "lower_bound", "upper_bound", "rate_percent", "effective_from", "effective_to", "rule_set", "legal_instrument", "legal_reference_detail"],
        order_by="sequence asc",
    )


def _wage_region(name: str | None, when):
    if not name:
        return None
    row = frappe.db.get_value(
        "VN Wage Region", name,
        ["name", "monthly_minimum_wage", "effective_from", "effective_to", "legal_instrument", "legal_reference_detail", "reference_status"], as_dict=True,
    )
    if not row or row.reference_status != "Released":
        return None
    when = getdate(when)
    if getdate(row.effective_from) > when or (row.effective_to and getdate(row.effective_to) < when):
        return None
    return row


def _line(line_type: str, amount, base=0, rate=0, floor=0, ceiling=0, rule=None, evidence=None):
    return {
        "line_type": line_type, "base_amount": money(base), "rate_percent": d(rate),
        "floor_amount": money(floor), "ceiling_amount": money(ceiling), "amount": money(amount),
        "rule_code": rule.code if rule else None, "rule_set": rule.rule_set if rule else None,
        "legal_instrument": rule.legal_instrument if rule else None,
        "legal_reference_detail": rule.legal_reference_detail if rule else None,
        "evidence": evidence or {},
    }


def calculate_salary_slip(doc) -> dict:
    settings = _settings(doc.company)
    if not settings or not settings.enable_payroll_compliance:
        return {"enabled": False, "status": "Not enabled", "blockers": [], "warnings": [], "lines": []}

    when = getdate(doc.end_date or doc.posting_date)
    blockers, warnings = [], []
    if doc.currency != "VND":
        blockers.append("P2 payroll compliance currently requires Salary Slip currency VND.")
    if doc.payroll_frequency != "Monthly":
        blockers.append("P2 PIT engine currently supports Monthly Salary Slips only; no proration is inferred.")

    tax_profile = _single_active(
        "VN Employee Tax Profile", {"employee": doc.employee}, when,
        ["name", "residency", "withholding_mode", "tax_identification_number", "effective_from", "effective_to", "rule_set"],
    )
    if not tax_profile:
        blockers.append("No active VN Employee Tax Profile for this employee.")

    social_profile = None
    if settings.enable_social_insurance:
        social_profile = _single_active(
            "VN Social Insurance Profile", {"employee": doc.employee}, when,
            ["name", "participate_bhxh", "participate_bhyt", "participate_bhtn", "participate_oai", "wage_region", "contribution_category", "effective_from", "effective_to", "rule_set"],
        )
        if not social_profile:
            blockers.append("No active VN Social Insurance Profile for this employee.")
        elif social_profile.contribution_category not in ("Ordinary", "Exempt"):
            blockers.append(f"Social insurance category {social_profile.contribution_category} requires manual/special rules not implemented in P2A.")

    taxable_income = Decimal("0")
    raw_bases = {"bhxh": Decimal("0"), "bhyt": Decimal("0"), "bhtn": Decimal("0")}
    component_evidence = []
    for row in doc.earnings:
        if getattr(row, "statistical_component", 0) or getattr(row, "do_not_include_in_total", 0):
            continue
        meta = _component_meta(row.salary_component)
        if meta.get("vn_compliance_review_status") != "Reviewed":
            blockers.append(f"Salary Component {row.salary_component} has not been reviewed for VN payroll compliance.")
            continue
        amount = d(row.amount)
        ratio = d(meta.get("vn_pit_taxable_ratio") or 0)
        if ratio < 0 or ratio > 100:
            blockers.append(f"Salary Component {row.salary_component} has invalid VN PIT taxable ratio.")
            continue
        if meta.get("vn_pit_taxable"):
            taxable_income += amount * ratio / Decimal("100")
        if meta.get("vn_bhxh_base_included"):
            raw_bases["bhxh"] += amount
        if meta.get("vn_bhyt_base_included"):
            raw_bases["bhyt"] += amount
        if meta.get("vn_bhtn_base_included"):
            raw_bases["bhtn"] += amount
        component_evidence.append({
            "component": row.salary_component, "amount": str(money(amount)), "pit_taxable": bool(meta.get("vn_pit_taxable")),
            "pit_ratio": str(ratio), "bhxh": bool(meta.get("vn_bhxh_base_included")),
            "bhyt": bool(meta.get("vn_bhyt_base_included")), "bhtn": bool(meta.get("vn_bhtn_base_included")),
            "legal_rule": meta.get("vn_legal_rule"),
        })

    lines = []
    employee_insurance = Decimal("0")
    employer_insurance = Decimal("0")
    if settings.enable_social_insurance and social_profile and social_profile.contribution_category == "Ordinary":
        ref = _rate("SI.REFERENCE_LEVEL", when)
        if not ref:
            blockers.append("No released SI.REFERENCE_LEVEL for payroll date.")
        else:
            floor = d(ref.decimal_value); ceiling = floor * Decimal("20")
            bhxh_base = clamp_contribution_base(raw_bases["bhxh"], floor, ceiling) if social_profile.participate_bhxh else Decimal("0")
            bhyt_base = clamp_contribution_base(raw_bases["bhyt"], floor, ceiling) if social_profile.participate_bhyt else Decimal("0")
            wage_region = _wage_region(social_profile.wage_region, when) if social_profile.participate_bhtn else None
            if social_profile.participate_bhtn and not wage_region:
                blockers.append("A released effective VN Wage Region is required for BHTN.")
                bhtn_base = Decimal("0")
            else:
                region_min = d(wage_region.monthly_minimum_wage) if wage_region else Decimal("0")
                bhtn_base = clamp_contribution_base(raw_bases["bhtn"], region_min, region_min * Decimal("20")) if social_profile.participate_bhtn else Decimal("0")

            for line_type, base_amount, rate_code, is_employee, floor_amt, ceiling_amt in [
                ("BHXH_EE", bhxh_base, "SI.BHXH_EE_RATE", True, floor, ceiling),
                ("BHXH_ER", bhxh_base, "SI.BHXH_ER_RATE", False, floor, ceiling),
                ("BHYT_EE", bhyt_base, "SI.BHYT_EE_RATE", True, floor, ceiling),
                ("BHYT_ER", bhyt_base, "SI.BHYT_ER_RATE", False, floor, ceiling),
                ("BHTN_EE", bhtn_base, "SI.BHTN_EE_RATE", True, d(wage_region.monthly_minimum_wage) if wage_region else 0, d(wage_region.monthly_minimum_wage) * 20 if wage_region else 0),
                ("BHTN_ER", bhtn_base, "SI.BHTN_ER_RATE", False, d(wage_region.monthly_minimum_wage) if wage_region else 0, d(wage_region.monthly_minimum_wage) * 20 if wage_region else 0),
                ("OAI_ER", bhxh_base if social_profile.participate_oai else 0, "SI.OAI_ER_RATE", False, floor, ceiling),
            ]:
                if d(base_amount) <= 0:
                    continue
                rate = _rate(rate_code, when)
                if not rate:
                    blockers.append(f"No released {rate_code} for payroll date.")
                    continue
                amount = contribution_amount(base_amount, rate.decimal_value)
                lines.append(_line(line_type, amount, base_amount, rate.decimal_value, floor_amt, ceiling_amt, rate))
                if is_employee:
                    employee_insurance += amount
                else:
                    employer_insurance += amount
    elif social_profile and social_profile.contribution_category == "Exempt":
        warnings.append("Employee social-insurance profile is Exempt; no compulsory contribution lines were calculated.")

    taxable_income = money(taxable_income)
    lines.append(_line("PIT_TAXABLE_INCOME", taxable_income, taxable_income, evidence={"components": component_evidence}))
    lines.append(_line("PIT_INSURANCE_DEDUCTION", employee_insurance, employee_insurance))

    pit = Decimal("0")
    if tax_profile:
        if tax_profile.residency == "Resident" and tax_profile.withholding_mode == "Progressive Payroll":
            personal_rule = _rate("PIT.PERSONAL_DEDUCTION_MONTHLY", when)
            dependent_rule = _rate("PIT.DEPENDENT_DEDUCTION_MONTHLY", when)
            brackets = _pit_brackets(when)
            if not personal_rule or not dependent_rule or len(brackets) != 5:
                blockers.append("Incomplete released PIT resident rule set for payroll date.")
            else:
                dependents = _active_dependents(doc.employee, when)
                personal = money(personal_rule.decimal_value)
                dependent = money(d(dependent_rule.decimal_value) * len(dependents))
                assessable = resident_assessable_income(taxable_income, employee_insurance, personal, dependent)
                pit = progressive_tax(assessable, brackets)
                lines.extend([
                    _line("PIT_PERSONAL_DEDUCTION", personal, personal, rule=personal_rule),
                    _line("PIT_DEPENDENT_DEDUCTION", dependent, dependent, rule=dependent_rule, evidence={"dependent_count": len(dependents), "dependent_ids": [x.name for x in dependents]}),
                    _line("PIT_ASSESSABLE_INCOME", assessable, assessable, evidence={"brackets": [dict(x) for x in brackets]}),
                    _line("PIT_WITHHOLDING", pit, assessable, rule=brackets[0], evidence={"method": "progressive_monthly_5_brackets"}),
                ])
        elif tax_profile.residency == "Nonresident" and tax_profile.withholding_mode == "Nonresident 20%":
            rate = _rate("PIT.NONRESIDENT_SALARY_RATE", when)
            if not rate:
                blockers.append("No released nonresident salary PIT rate for payroll date.")
            else:
                pit = nonresident_salary_tax(taxable_income, rate.decimal_value)
                lines.extend([
                    _line("PIT_ASSESSABLE_INCOME", taxable_income, taxable_income, evidence={"method": "nonresident_gross_taxable_salary"}),
                    _line("PIT_WITHHOLDING", pit, taxable_income, rate.decimal_value, rule=rate),
                ])
        else:
            blockers.append("Employee tax residency/withholding mode requires manual review.")

    canonical = {
        "employee": doc.employee, "company": doc.company, "date": str(when),
        "currency": doc.currency, "payroll_frequency": doc.payroll_frequency,
        "tax_profile": tax_profile.name if tax_profile else None,
        "social_profile": social_profile.name if social_profile else None,
        "lines": [{k: (str(v) if isinstance(v, Decimal) else v) for k, v in line.items()} for line in lines],
        "warnings": sorted(set(warnings)), "blockers": sorted(set(blockers)),
    }
    snapshot_hash = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
    return {
        "enabled": True, "status": "Ready" if not blockers else "Needs Review",
        "blockers": sorted(set(blockers)), "warnings": sorted(set(warnings)), "lines": lines,
        "pit": money(pit), "employee_insurance": money(employee_insurance), "employer_insurance": money(employer_insurance),
        "snapshot_hash": snapshot_hash, "canonical": canonical,
    }


def validate_salary_slip(doc, method=None):
    result = calculate_salary_slip(doc)
    if not result.get("enabled"):
        if hasattr(doc, "vn_payroll_compliance_status"):
            doc.vn_payroll_compliance_status = "Not enabled"
        return
    doc.vn_payroll_compliance_status = result["status"]
    doc.vn_pit_calculated = float(result["pit"])
    doc.vn_employee_insurance_total = float(result["employee_insurance"])
    doc.vn_employer_insurance_total = float(result["employer_insurance"])
    doc.vn_payroll_snapshot_hash = result["snapshot_hash"]
    if result["blockers"]:
        frappe.throw("VN payroll compliance blockers:\n- " + "\n- ".join(result["blockers"]))


def snapshot_salary_slip(doc, method=None):
    result = calculate_salary_slip(doc)
    if not result.get("enabled"):
        return
    if result["blockers"]:
        frappe.throw("Cannot snapshot VN payroll evidence while blockers remain")
    for line in result["lines"]:
        key = f"{doc.name}::{line['line_type']}"
        existing = frappe.db.get_value("VN Payroll Calculation Line", key, "snapshot_hash")
        if existing:
            if existing != result["snapshot_hash"]:
                frappe.throw(f"Existing immutable VN payroll evidence differs for {key}")
            continue
        frappe.get_doc({
            "doctype": "VN Payroll Calculation Line", "line_key": key,
            "salary_slip": doc.name, "employee": doc.employee, "company": doc.company,
            "posting_date": doc.end_date or doc.posting_date, "line_type": line["line_type"],
            "base_amount": float(line["base_amount"]), "rate_percent": float(line["rate_percent"]),
            "floor_amount": float(line["floor_amount"]), "ceiling_amount": float(line["ceiling_amount"]),
            "amount": float(line["amount"]), "currency": doc.currency,
            "rule_code": line["rule_code"], "rule_set": line["rule_set"],
            "legal_instrument": line["legal_instrument"], "legal_reference_detail": line["legal_reference_detail"],
            "snapshot_hash": result["snapshot_hash"],
            "evidence_json": json.dumps(line.get("evidence") or {}, sort_keys=True, default=str),
        }).insert(ignore_permissions=True)
