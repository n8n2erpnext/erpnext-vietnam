from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

import frappe
from frappe.utils import getdate

from erpnext_vietnam.declarations.adapters.base import AdapterResult
from erpnext_vietnam.declarations.adapters.vat_tt89_math import deductible_input_vat, derive_01_gtgt
from erpnext_vietnam.declarations.vat_reporting import aggregate_reporting_lines
from erpnext_vietnam.payroll.reconciliation import reconcile_salary_slip

ADAPTER_VERSION = "tt89-2026-v1"
LEGAL_SOURCE = "89/2026/TT-BTC"
EFFECTIVE_FROM = getdate("2026-07-01")

FORM_05_KK_INDICATORS = {
    "15": "Total employees/individuals receiving salary or wages",
    "16": "Resident individuals with labour contracts",
    "17": "Individuals from whom PIT was withheld",
    "18": "Resident individuals from whom PIT was withheld",
    "19": "Nonresident individuals from whom PIT was withheld",
    "20": "Taxable salary/wage income paid",
    "21": "Taxable income paid to residents",
    "22": "Taxable income paid to nonresidents",
    "23": "Foreign life/non-compulsory insurance premium income",
    "24": "Total exempt income",
    "25": "Exempt oil/gas contract income",
    "26": "Exempt science/technology/innovation-task income",
    "27": "Exempt startup expert income",
    "28": "Other exempt income",
    "29": "Taxable income subject to withholding",
    "30": "Resident taxable income subject to withholding",
    "31": "Nonresident taxable income subject to withholding",
    "32": "Assessable income",
    "33": "Resident assessable income",
    "34": "Nonresident assessable income",
    "35": "PIT required to be withheld",
    "36": "PIT exempt in the period",
    "37": "Income of eligible high-quality digital-industry personnel",
    "38": "Corresponding digital-industry PIT exemption",
    "39": "Income of eligible high-tech personnel",
    "40": "Corresponding high-tech PIT exemption",
    "41": "Other PIT exemption",
    "42": "PIT actually withheld",
    "43": "PIT actually withheld from residents",
    "44": "PIT actually withheld from nonresidents",
    "45": "PIT withheld on relevant foreign insurance premium",
}

FORM_05_QTT_INDICATORS = {
    "15": "Total employees/individuals receiving salary or wages",
    "16": "Resident individuals with labour contracts",
    "17": "Individuals from whom PIT was withheld",
    "18": "Resident individuals from whom PIT was withheld",
    "19": "Nonresident individuals from whom PIT was withheld",
    "20": "Individuals eligible for DTA exemption/reduction",
    "21": "Individuals applying family deduction",
    "22": "Taxable salary/wage income paid",
    "23": "Taxable income paid to residents",
    "24": "Taxable income paid to nonresidents",
    "25": "Foreign life/non-compulsory insurance premium income",
    "26": "Total exempt income",
    "27": "Exempt oil/gas contract income",
    "28": "Exempt science/technology/innovation-task income",
    "29": "Exempt startup expert income",
    "30": "Taxable income subject to withholding",
    "31": "Resident taxable income subject to withholding",
    "32": "Nonresident taxable income subject to withholding",
    "33": "PIT actually withheld",
    "34": "PIT actually withheld from residents",
    "35": "PIT actually withheld from nonresidents",
    "36": "PIT withheld on relevant foreign insurance premium",
    "37": "Individuals authorizing employer finalization",
    "38": "PIT withheld for authorized finalization individuals",
    "39": "PIT withheld by prior organization before transfer",
    "40": "PIT payable for authorized finalization individuals",
    "41": "PIT exempt because residual payable does not exceed statutory threshold",
    "42": "Digital-industry personnel PIT exemption",
    "43": "High-tech personnel PIT exemption",
    "44": "Additional PIT payable after finalization",
    "45": "PIT overpaid after finalization",
}

FORM_01_GTGT_INDICATORS = {
    "21": "No purchase/sale activity marker",
    "22": "Deductible input VAT carried from prior period",
    "23": "Value of purchased goods/services",
    "24": "Input VAT on purchased goods/services",
    "23a": "Value of imported purchased goods/services",
    "24a": "Input VAT on imported purchased goods/services",
    "25": "Deductible input VAT",
    "26": "Non-taxable sales",
    "27": "Taxable sales value",
    "28": "Output VAT",
    "29": "Zero-rated sales",
    "30": "5% rated sales",
    "31": "VAT on 5% rated sales",
    "32": "10% rated sales",
    "33": "VAT on 10% rated sales",
    "32a": "Sales not declared/tax-paid in this declaration",
    "32b": "Sales not included in the VAT tax base",
    "34a": "Sales outside scope of VAT law",
    "34": "Total sales value",
    "35": "Total output VAT",
    "36": "VAT arising",
    "37": "Increase adjustment of deductible input VAT",
    "38": "Decrease adjustment of deductible input VAT",
    "39a": "Deductible VAT transferred from investment project/subordinate unit",
    "40a": "VAT payable from business activities",
    "40b": "VAT from separate 02/GTGT calculation",
    "40": "VAT still payable after netting",
    "41": "VAT not fully deductible",
    "42": "VAT refund requested",
    "43": "Deductible VAT carried to next period",
}


def _decimal(value) -> Decimal:
    return Decimal(str(value or 0))


def _active_tax_profile(employee: str, when):
    when = getdate(when)
    rows = frappe.get_all(
        "VN Employee Tax Profile",
        filters={"employee": employee, "effective_from": ["<=", when]},
        fields=["name", "residency", "tax_identification_number", "withholding_mode", "effective_from", "effective_to", "rule_set"],
        order_by="effective_from desc",
    )
    rows = [row for row in rows if not row.effective_to or getdate(row.effective_to) >= when]
    return dict(rows[0]) if rows else None


def _payroll_split(canonical: dict) -> dict:
    slips = canonical.get("source_salary_slips") or []
    employee_totals = {row["employee"]: row.get("totals") or {} for row in canonical.get("employees") or []}
    by_residency = defaultdict(lambda: defaultdict(lambda: Decimal("0")))
    withheld_people = defaultdict(set)
    profiles = []
    missing_profiles = []
    actual_withheld = defaultdict(lambda: Decimal("0"))
    actual_reconciliation_failures = []

    for slip in slips:
        employee = slip.get("employee")
        when = slip.get("end_date")
        profile = _active_tax_profile(employee, when) if employee and when else None
        if not profile or profile.get("residency") not in {"Resident", "Nonresident"}:
            missing_profiles.append(slip.get("name"))
            residency = "Unknown"
        else:
            residency = profile["residency"]
            profiles.append({"salary_slip": slip.get("name"), **profile})

        # Employee totals are aggregated across the declaration period. For multi-slip periods,
        # split amounts must instead be reconstructed from immutable evidence by slip below.
        evidence = frappe.get_all(
            "VN Payroll Calculation Line",
            filters={"salary_slip": slip.get("name")},
            fields=["line_type", "amount"],
            limit_page_length=0,
        ) if slip.get("name") else []
        for row in evidence:
            by_residency[residency][row.line_type] += _decimal(row.amount)
            if row.line_type == "PIT_WITHHOLDING" and _decimal(row.amount) > 0 and employee:
                withheld_people[residency].add(employee)

        if slip.get("name"):
            recon = reconcile_salary_slip(slip["name"])
            pit_row = next((row for row in recon.get("rows", []) if row.get("code") == "PIT_WITHHOLDING"), None)
            if recon.get("status") == "MATCH" and pit_row:
                actual_withheld[residency] += _decimal(pit_row.get("actual"))
            else:
                actual_reconciliation_failures.append({"salary_slip": slip["name"], "status": recon.get("status")})

    return {
        "by_residency": by_residency,
        "withheld_people": withheld_people,
        "profiles": profiles,
        "missing_profiles": sorted(set(filter(None, missing_profiles))),
        "actual_withheld": actual_withheld,
        "actual_reconciliation_failures": actual_reconciliation_failures,
        "employee_count": canonical.get("summary", {}).get("employee_count", len(employee_totals)),
    }


def _sum(split: dict, line_type: str) -> Decimal:
    return sum((_decimal(split["by_residency"][key].get(line_type)) for key in ("Resident", "Nonresident")), Decimal("0"))


def _explicit_indicators(canonical: dict, allowed: set[str]) -> dict:
    values = canonical.get("statutory_inputs") or {}
    if not isinstance(values, dict):
        frappe.throw("statutory_inputs must be a JSON object")
    return {str(key): value for key, value in values.items() if str(key) in allowed}


def _apply_explicit(indicators: dict, canonical: dict) -> None:
    for key, value in _explicit_indicators(canonical, set(indicators)).items():
        indicators[key] = value


def _missing_indicators(indicators: dict, keys: list[str] | tuple[str, ...]) -> list[str]:
    return [f"[{key}] explicit statutory value/classification" for key in keys if indicators.get(key) is None]


def _validate_sum(indicators: dict, total: str, parts: tuple[str, ...], warnings: list[str]) -> None:
    if any(indicators.get(key) is None for key in (total, *parts)):
        return
    expected = sum((_decimal(indicators[key]) for key in parts), Decimal("0"))
    if _decimal(indicators[total]) != expected:
        warnings.append(f"Indicator [{total}] does not equal " + " + ".join(f"[{key}]" for key in parts))


def adapt_05_kk_tncn(canonical: dict) -> dict:
    split = _payroll_split(canonical)
    r = split["by_residency"]["Resident"]
    n = split["by_residency"]["Nonresident"]
    indicators = {key: None for key in FORM_05_KK_INDICATORS}
    indicators.update({
        "15": split["employee_count"],
        "17": len(split["withheld_people"]["Resident"] | split["withheld_people"]["Nonresident"]),
        "18": len(split["withheld_people"]["Resident"]),
        "19": len(split["withheld_people"]["Nonresident"]),
        "20": _sum(split, "PIT_TAXABLE_INCOME"),
        "21": _decimal(r.get("PIT_TAXABLE_INCOME")),
        "22": _decimal(n.get("PIT_TAXABLE_INCOME")),
        "32": _sum(split, "PIT_ASSESSABLE_INCOME"),
        "33": _decimal(r.get("PIT_ASSESSABLE_INCOME")),
        "34": _decimal(n.get("PIT_ASSESSABLE_INCOME")),
        "35": _sum(split, "PIT_WITHHOLDING"),
    })
    _apply_explicit(indicators, canonical)
    missing = _missing_indicators(indicators, ["16", "23", "24", "25", "26", "27", "28", "29", "30", "31", "36", "37", "38", "39", "40", "41", "45"])
    warnings = []
    if split["missing_profiles"]:
        missing.append("Resident/nonresident profile for all source Salary Slips")
        warnings.append("Some source Salary Slips lack an effective Resident/Nonresident VN Employee Tax Profile.")
    if split["actual_reconciliation_failures"]:
        missing.append("Exact actual PIT withholding reconciliation for all source Salary Slips")
        warnings.append("Some source Salary Slips do not reconcile exactly to HRMS deductions.")
    else:
        indicators.update({
            "42": split["actual_withheld"]["Resident"] + split["actual_withheld"]["Nonresident"],
            "43": split["actual_withheld"]["Resident"],
            "44": split["actual_withheld"]["Nonresident"],
        })
    _apply_explicit(indicators, canonical)
    _validate_sum(indicators, "17", ("18", "19"), missing)
    _validate_sum(indicators, "20", ("21", "22"), missing)
    _validate_sum(indicators, "24", ("25", "26", "27", "28"), missing)
    _validate_sum(indicators, "29", ("30", "31"), missing)
    _validate_sum(indicators, "32", ("33", "34"), missing)
    _validate_sum(indicators, "42", ("43", "44"), missing)
    missing.extend(_missing_indicators(indicators, ["42", "43", "44"]))
    result = AdapterResult(
        form_code="05/KK-TNCN", adapter_version=ADAPTER_VERSION, legal_source=LEGAL_SOURCE,
        indicators=indicators, missing_required=missing, warnings=warnings,
        source_refs=split["profiles"],
    )
    return result.as_dict()


def adapt_05_qtt_tncn(canonical: dict) -> dict:
    split = _payroll_split(canonical)
    r = split["by_residency"]["Resident"]
    n = split["by_residency"]["Nonresident"]
    indicators = {key: None for key in FORM_05_QTT_INDICATORS}
    indicators.update({
        "15": split["employee_count"],
        "17": len(split["withheld_people"]["Resident"] | split["withheld_people"]["Nonresident"]),
        "18": len(split["withheld_people"]["Resident"]),
        "19": len(split["withheld_people"]["Nonresident"]),
        "22": _sum(split, "PIT_TAXABLE_INCOME"),
        "23": _decimal(r.get("PIT_TAXABLE_INCOME")),
        "24": _decimal(n.get("PIT_TAXABLE_INCOME")),
    })
    _apply_explicit(indicators, canonical)
    missing = _missing_indicators(indicators, ["16", "20", "21", "25", "26", "27", "28", "29", "30", "31", "32", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45"])
    warnings = []
    if not canonical.get("annual_annexes_reviewed"):
        missing.append("05-1/05-2/05-3 annual finalization annex data reviewed against TT89")
    if split["missing_profiles"]:
        missing.append("Resident/nonresident profile for all source Salary Slips")
        warnings.append("Some source Salary Slips lack an effective Resident/Nonresident VN Employee Tax Profile.")
    if split["actual_reconciliation_failures"]:
        missing.append("Exact actual PIT withholding reconciliation for all source Salary Slips")
    else:
        indicators.update({
            "33": split["actual_withheld"]["Resident"] + split["actual_withheld"]["Nonresident"],
            "34": split["actual_withheld"]["Resident"],
            "35": split["actual_withheld"]["Nonresident"],
        })
    _apply_explicit(indicators, canonical)
    _validate_sum(indicators, "17", ("18", "19"), missing)
    _validate_sum(indicators, "22", ("23", "24"), missing)
    _validate_sum(indicators, "26", ("27", "28", "29"), missing)
    _validate_sum(indicators, "30", ("31", "32"), missing)
    _validate_sum(indicators, "33", ("34", "35"), missing)
    missing.extend(_missing_indicators(indicators, ["33", "34", "35"]))
    return AdapterResult(
        form_code="05/QTT-TNCN", adapter_version=ADAPTER_VERSION, legal_source=LEGAL_SOURCE,
        indicators=indicators, missing_required=missing, warnings=warnings,
        source_refs=split["profiles"],
    ).as_dict()


def adapt_01_gtgt(canonical: dict) -> dict:
    lines = canonical.get("reporting_lines") or []
    source_docs = canonical.get("source_documents") or []
    sales_count = sum(1 for row in source_docs if row.get("doctype") == "Sales Invoice")
    purchase_count = sum(1 for row in source_docs if row.get("doctype") == "Purchase Invoice")
    aggregated, reporting_missing, warnings = aggregate_reporting_lines(lines)
    deductible, deduction_missing, deduction_warnings = deductible_input_vat(lines)
    warnings.extend(deduction_warnings)
    missing = list(reporting_missing) + list(deduction_missing)

    if canonical.get("company_currency") != "VND":
        missing.append("01/GTGT canonical amounts must be normalized to VND")

    for line in lines:
        category = line.get("reporting_category") or {}
        label = f"{line.get('doctype')} {line.get('parent')} row {line.get('idx')}"
        if category:
            if not line.get("reporting_snapshot_hash"):
                missing.append(f"{label}: immutable VAT reporting snapshot hash")
            elif not line.get("reporting_snapshot_hash_matches"):
                missing.append(f"{label}: VAT reporting snapshot hash must match released category")
        if line.get("reporting_error"):
            missing.append(f"{label}: valid released VAT reporting category")
        if category.get("requires_reduction_annex"):
            missing.append(f"{label}: TT89 temporary VAT-reduction annex row/export evidence")

    manual = _explicit_indicators(canonical, set(FORM_01_GTGT_INDICATORS))
    derived, closing_missing = derive_01_gtgt(aggregated, deductible, manual)
    indicators = {key: None for key in FORM_01_GTGT_INDICATORS}
    indicators.update(derived)
    indicators["21"] = bool(sales_count == 0 and purchase_count == 0)
    missing.extend(f"[{key}] explicit statutory closing/adjustment input" for key in closing_missing)

    if indicators.get("42") is not None and indicators.get("41") is not None and _decimal(indicators["42"]) > _decimal(indicators["41"]):
        missing.append("[42] refund request cannot exceed [41] remaining deductible VAT")
    if indicators.get("40") is not None and _decimal(indicators["40"]) < 0:
        missing.append("[40b] cannot make [40] VAT payable negative")

    return AdapterResult(
        form_code="01/GTGT", adapter_version=ADAPTER_VERSION, legal_source=LEGAL_SOURCE,
        indicators=indicators, missing_required=missing, warnings=warnings,
        source_refs=source_docs,
    ).as_dict()


def adapt_tax_declaration(canonical: dict) -> dict:
    period = canonical.get("period") or {}
    code = canonical.get("form_code")
    from_date = getdate(period["from_date"]) if period.get("from_date") else None
    if code in {"01/GTGT", "05/KK-TNCN"} and from_date and from_date < EFFECTIVE_FROM:
        frappe.throw("TT89 adapter cannot be applied to this periodic declaration before 2026-07-01")
    if code == "05/QTT-TNCN" and from_date and from_date.year < 2026:
        frappe.throw("TT89 annual finalization adapter supports tax year 2026 onward")
    if code == "01/GTGT":
        return adapt_01_gtgt(canonical)
    if code == "05/KK-TNCN":
        return adapt_05_kk_tncn(canonical)
    if code == "05/QTT-TNCN":
        return adapt_05_qtt_tncn(canonical)
    frappe.throw(f"Unsupported TT89 form code: {code}")
