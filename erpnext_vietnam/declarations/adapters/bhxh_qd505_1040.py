from __future__ import annotations

from erpnext_vietnam.declarations.adapters.base import AdapterResult

ADAPTER_VERSION = "bhxh-qd505-1040-v1"
LEGAL_SOURCE = "QĐ 505/QĐ-BHXH (TK1-TS/TK3-TS) + QĐ 1040/QĐ-BHXH (D02-LT)"

TK1_INDICATORS = {
    "01": "Full name",
    "02": "Gender",
    "03": "Date of birth",
    "04": "Nationality",
    "05": "Ethnicity",
    "06": "Citizen ID/ID card/passport",
    "07": "Phone",
    "08": "Email",
    "09.1": "Birth registration commune/ward",
    "09.2": "Birth registration district",
    "09.3": "Birth registration province/city",
    "10": "Parent/guardian for child under 6",
    "11.1": "Result address - house/street/hamlet",
    "11.2": "Result address - commune/ward",
    "11.3": "Result address - district",
    "11.4": "Result address - province/city",
    "12": "Household-member appendix attached",
    "13": "Social-insurance number",
    "14.1": "Adjusted full name",
    "14.2": "Adjusted gender",
    "14.3": "Adjusted date of birth",
    "14.4": "Adjusted birth-registration place",
    "14.5": "Adjusted citizen ID/ID card/passport",
    "15": "Voluntary contribution amount",
    "16": "Contribution method",
    "17": "Initial health-care facility",
    "18": "Other requested change",
    "19": "Attached evidence",
}

TK3_INDICATORS = {
    "01": "Employer/unit name",
    "02": "BHXH unit code",
    "03": "Tax identification number",
    "04": "Registered business address",
    "05": "Unit/entity type",
    "06": "Main business activity",
    "07": "Transaction/contact address",
    "08": "Phone",
    "09": "Email",
    "10.1": "Establishment/business registration number",
    "10.2": "Issuing authority",
    "11": "Alternative contribution method",
    "12": "Change/request content",
    "13": "Attached documents",
}

D02_COLUMNS = {
    "1": "Sequence number",
    "2": "Full name",
    "3": "Social-insurance number",
    "4": "Date of birth",
    "5": "Gender",
    "6": "Citizen ID/ID card/passport",
    "7": "Rank/position/job title/workplace",
    "8": "Manager occupational group",
    "9": "High-level technical professional group",
    "10": "Mid-level technical professional group",
    "11": "Other occupational group",
    "12": "Salary coefficient/amount",
    "13": "Position allowance",
    "14": "Seniority beyond frame (%)",
    "15": "Occupational seniority (%)",
    "16": "Wage allowance",
    "17": "Other additions",
    "18": "Hazardous occupation start date",
    "19": "Hazardous occupation end date",
    "20": "Indefinite labour contract start date",
    "21": "Fixed-term labour contract start date",
    "22": "Fixed-term labour contract end date",
    "23": "Other/probation contract start date",
    "24": "Other/probation contract end date",
    "25": "BHXH contribution start date at unit",
    "26": "BHXH contribution end date at unit",
    "27": "Notes / contract or decision details",
}


D02_HEADER_FIELDS = {
    "unit_name": "Employer/unit name",
    "document_number": "D02-LT document number",
    "unit_code": "BHXH unit code",
    "tax_id": "Tax identification number",
    "address": "Employer address",
    "phone": "Employer phone",
    "email": "Employer email",
    "signed_place": "Signing place",
    "signed_date": "Signing date",
}


def _explicit_indicators(canonical: dict) -> dict:
    values = canonical.get("statutory_inputs") or {}
    if not isinstance(values, dict):
        raise ValueError("statutory_inputs must be an object")
    indicators = values.get("indicators") if isinstance(values.get("indicators"), dict) else values
    return {str(key): value for key, value in indicators.items()}


def _merge_indicators(indicators: dict, canonical: dict) -> set[str]:
    explicit = _explicit_indicators(canonical)
    provided = set()
    for key, value in explicit.items():
        if key in indicators:
            indicators[key] = value
            provided.add(key)
    return provided


def _filing_mode(canonical: dict) -> str | None:
    values = canonical.get("statutory_inputs") or {}
    return values.get("filing_mode") if isinstance(values, dict) else None


def _statutory_row_overrides(canonical: dict) -> dict[str, dict]:
    result = {}
    for row in canonical.get("statutory_rows") or []:
        key = row.get("source_salary_slip")
        if key and isinstance(row.get("columns"), dict):
            result[key] = row
    return result


def adapt_tk1_ts(canonical: dict) -> dict:
    employee = canonical.get("employee") or {}
    profile = canonical.get("social_insurance_profile") or {}
    indicators = {key: None for key in TK1_INDICATORS}
    indicators.update({
        "01": employee.get("employee_name"),
        "02": employee.get("gender"),
        "03": employee.get("date_of_birth"),
        "06": employee.get("passport_number"),
        "07": employee.get("cell_number"),
        "08": employee.get("personal_email"),
        "11.1": employee.get("current_address") or employee.get("permanent_address"),
        "13": profile.get("social_insurance_number"),
    })
    explicit = _merge_indicators(indicators, canonical)
    mode = _filing_mode(canonical)
    missing = []
    warnings = [
        "Passport/identity data is carried as source evidence but is not classified as Vietnamese CCCD unless explicitly reviewed.",
    ]
    if mode not in {"New", "Adjustment"}:
        missing.append("Explicit TK1-TS filing_mode: New or Adjustment")
    required_identity = ("01", "02", "03", "04", "05", "06", "07", "09.1", "09.2", "09.3", "11.1", "11.2", "11.3", "11.4")
    for key in required_identity:
        if indicators.get(key) in (None, ""):
            missing.append(f"TK1-TS [{key}] required participant field")
    if mode == "Adjustment":
        if indicators.get("13") in (None, ""):
            missing.append("TK1-TS [13] statutory BHXH number for adjustment mode")
        adjustment_keys = ("14.1", "14.2", "14.3", "14.4", "14.5", "15", "16", "17", "18", "19")
        if not any(key in explicit for key in adjustment_keys):
            missing.append("TK1-TS adjustment mode requires at least one explicitly reviewed [14]-[19] change/request field")
    return AdapterResult(
        form_code="TK1-TS", adapter_version=ADAPTER_VERSION, legal_source=LEGAL_SOURCE,
        indicators=indicators, missing_required=missing, warnings=warnings,
        source_refs=[{"employee": employee.get("name"), "source_sha256": canonical.get("source_sha256")}],
    ).as_dict()


def adapt_tk3_ts(canonical: dict) -> dict:
    company = canonical.get("company") or {}
    indicators = {key: None for key in TK3_INDICATORS}
    indicators.update({
        "01": company.get("company_name") or company.get("name"),
        "03": company.get("tax_id"),
        "08": company.get("phone_no"),
        "09": company.get("email"),
        "10.1": company.get("registration_details"),
    })
    explicit = _merge_indicators(indicators, canonical)
    missing = []
    for key in ("01", "03", "04", "05", "06", "07", "08", "09", "10.1", "10.2"):
        if indicators.get(key) in (None, ""):
            missing.append(f"TK3-TS [{key}] required/reviewed employer field")
    # [02] may legally be blank where the unit has not yet been assigned a BHXH code.
    if "02" not in explicit and indicators.get("02") in (None, ""):
        missing.append("TK3-TS [02] explicit reviewed value (blank is allowed for a new unassigned unit)")
    return AdapterResult(
        form_code="TK3-TS", adapter_version=ADAPTER_VERSION, legal_source=LEGAL_SOURCE,
        indicators=indicators, missing_required=missing,
        warnings=["Company.registration_details is evidence only; official registration number/issuer must be explicitly reviewed."],
        source_refs=[{"company": company.get("name"), "source_sha256": canonical.get("source_sha256")}],
    ).as_dict()


def adapt_d02_lt(canonical: dict) -> dict:
    rows = []
    missing = []
    company = canonical.get("company_master") or {}
    inputs = canonical.get("statutory_inputs") or {}
    header_explicit = inputs.get("header") if isinstance(inputs.get("header"), dict) else {}
    header = {key: None for key in D02_HEADER_FIELDS}
    header.update({
        "unit_name": company.get("company_name") or company.get("name") or canonical.get("company"),
        "tax_id": company.get("tax_id"),
        "phone": company.get("phone_no"),
        "email": company.get("email"),
    })
    for key, value in header_explicit.items():
        if key in header:
            header[key] = value
    for key in D02_HEADER_FIELDS:
        if header.get(key) in (None, ""):
            missing.append(f"D02-LT header {key}: required/reviewed value")
    overrides = _statutory_row_overrides(canonical)
    for index, source in enumerate(canonical.get("rows") or [], start=1):
        employee = source.get("employee_master") or {}
        profile = source.get("social_insurance_profile") or {}
        row = {key: None for key in D02_COLUMNS}
        row.update({
            "1": index,
            "2": source.get("employee_name") or employee.get("employee_name"),
            "3": profile.get("social_insurance_number"),
            "4": employee.get("date_of_birth"),
            "5": employee.get("gender"),
            "6": employee.get("passport_number"),
            "7": employee.get("designation"),
        })
        override = overrides.get(source.get("salary_slip")) or {}
        explicit_columns = override.get("columns") or {}
        for key, value in explicit_columns.items():
            if str(key) in row:
                row[str(key)] = value
        label = source.get("salary_slip") or source.get("employee") or str(index)
        for key in ("2", "3", "4", "5", "6", "7", "12", "25", "27"):
            if row.get(key) in (None, ""):
                missing.append(f"D02-LT {label} [{key}] required/reviewed value")
        # Conditional columns are validly blank only after the accountant explicitly reviewed them.
        for key in ("8", "9", "10", "11", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "26"):
            if key not in explicit_columns:
                missing.append(f"D02-LT {label} [{key}] explicit reviewed value or N/A")
        rows.append({
            "columns": row,
            "source_salary_slip": source.get("salary_slip"),
            "source_snapshot_hash": source.get("snapshot_hash"),
            "insurance_evidence": {
                key: source.get(key) for key in (
                    "bhxh_base", "bhyt_base", "bhtn_base", "employee_bhxh", "employee_bhyt",
                    "employee_bhtn", "employer_bhxh", "employer_bhyt", "employer_bhtn", "employer_oai",
                )
            },
        })
    if not rows:
        missing.append("At least one source employee/payroll row")
    warnings = [
        "Insurance contribution bases remain evidence only and are never copied into D02-LT [12] without explicit wage decomposition.",
        "Employee join/contract dates are not treated as statutory BHXH participation or labour-contract dates without explicit review.",
    ]
    return AdapterResult(
        form_code="D02-LT", adapter_version=ADAPTER_VERSION, legal_source=LEGAL_SOURCE,
        indicators=header, rows=rows, missing_required=missing, warnings=warnings,
        source_refs=[{"salary_slip": row.get("salary_slip"), "snapshot_hash": row.get("snapshot_hash")} for row in canonical.get("rows") or []],
    ).as_dict()


def adapt_social_insurance_export(canonical: dict) -> dict:
    code = canonical.get("form_code")
    if code == "TK1-TS":
        return adapt_tk1_ts(canonical)
    if code == "TK3-TS":
        return adapt_tk3_ts(canonical)
    if code == "D02-LT":
        return adapt_d02_lt(canonical)
    raise ValueError(f"Unsupported BHXH form code: {code}")
