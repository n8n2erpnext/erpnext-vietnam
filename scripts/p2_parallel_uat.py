import argparse
import json
import os
from decimal import Decimal

import frappe
from frappe.utils import getdate

from erpnext_vietnam.payroll.service import calculate_salary_slip
from erpnext_vietnam.payroll.reconciliation import (
    employer_accrual_preview,
    reconcile_salary_slip,
)
from hrms.payroll.doctype.salary_structure.salary_structure import make_salary_slip

TAG = "P2-UAT-20260906"
PAY_DATE = "2026-09-30"
START_DATE = "2026-09-01"
BASIC_AMOUNT = Decimal("30000000")

def parse_args():
    parser = argparse.ArgumentParser(description="Rollback-only P2 parallel payroll UAT")
    parser.add_argument("--site", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--bench", required=True, help="Absolute Frappe bench path")
    return parser.parse_args()

def money(v):
    return Decimal(str(v or 0)).quantize(Decimal("1"))

def insert(doc):
    return frappe.get_doc(doc).insert(ignore_permissions=True)

def make_component(name, abbr, component_type, vn_meta=None):
    doc = frappe.get_doc({
        "doctype": "Salary Component",
        "salary_component": name,
        "salary_component_abbr": abbr,
        "type": component_type,
    })
    for key, value in (vn_meta or {}).items():
        setattr(doc, key, value)
    doc.insert(ignore_permissions=True)
    return doc

def make_temp_settings(company):
    return insert({
        "doctype": "VN Localization Settings",
        "company": company,
        "business_profile": "SOFTWARE_SAAS",
        "accounting_regime": "TT99_2025",
        "vat_method": "DEDUCTION",
        "vat_validation_mode": "Advisory",
        "enable_payroll_compliance": 1,
        "enable_social_insurance": 1,
        "enable_einvoice": 0,
        "enable_compliance_gateway": 0,
    })

def main():
    args = parse_args()
    company = args.company
    bench = os.path.abspath(args.bench)
    sites_path = os.path.join(bench, "sites")
    os.chdir(sites_path)
    frappe.init(site=args.site, sites_path=sites_path)
    frappe.connect()
    frappe.set_user("Administrator")
    frappe.flags.in_test = True
    try:
        assert frappe.db.exists("Company", company), f"Unknown Company: {company}"
        assert not frappe.db.exists("VN Localization Settings", company), "UAT requires payroll localization to be disabled before test"
        before_counts = {
            "journal_entries": frappe.db.count("Journal Entry"),
            "gl_entries": frappe.db.count("GL Entry"),
            "submissions": frappe.db.count("VN Submission"),
        }
        settings = make_temp_settings(company)
        wage = frappe.get_all(
            "VN Wage Region",
            filters={"reference_status": "Released", "effective_from": ["<=", PAY_DATE]},
            fields=["name", "code", "monthly_minimum_wage", "effective_from", "effective_to"],
            order_by="monthly_minimum_wage desc",
        )[0]
        gender = frappe.db.get_value("Gender", {}, "name")
        holiday = insert({
            "doctype": "Holiday List",
            "holiday_list_name": f"{TAG} Holidays",
            "from_date": "2026-01-01", "to_date": "2026-12-31",
        })
        employee = insert({
            "doctype": "Employee", "first_name": "VN P2 UAT", "gender": gender,
            "date_of_birth": "1990-01-01", "date_of_joining": "2026-01-01",
            "status": "Active", "company": company, "employee_number": TAG,
            "holiday_list": holiday.name,
        })
        hla = insert({
            "doctype": "Holiday List Assignment", "applicable_for": "Employee",
            "assigned_to": employee.name, "holiday_list": holiday.name,
            "from_date": "2026-01-01",
        })
        hla.submit()
        tax_profile = insert({
            "doctype": "VN Employee Tax Profile", "employee": employee.name,
            "residency": "Resident", "withholding_mode": "Progressive Payroll",
            "effective_from": "2026-01-01",
        })
        social_profile = insert({
            "doctype": "VN Social Insurance Profile", "employee": employee.name,
            "participate_bhxh": 1, "participate_bhyt": 1,
            "participate_bhtn": 1, "participate_oai": 1,
            "wage_region": wage.name, "contribution_category": "Ordinary",
            "effective_from": "2026-01-01",
        })
        reviewed_meta = {
            "vn_compliance_review_status": "Reviewed",
            "vn_pit_taxable": 1,
            "vn_pit_taxable_ratio": 100,
            "vn_bhxh_base_included": 1,
            "vn_bhyt_base_included": 1,
            "vn_bhtn_base_included": 1,
            "vn_regular_stable_payment": 1,
        }
        basic = make_component(f"{TAG} Basic", "UATB", "Earning", reviewed_meta)
        bxh = make_component(f"{TAG} BHXH", "UBXH", "Deduction", {"vn_compliance_review_status": "Reviewed"})
        byt = make_component(f"{TAG} BHYT", "UBYT", "Deduction", {"vn_compliance_review_status": "Reviewed"})
        btn = make_component(f"{TAG} BHTN", "UBTN", "Deduction", {"vn_compliance_review_status": "Reviewed"})
        pitc = make_component(f"{TAG} PIT", "UPIT", "Deduction", {"vn_compliance_review_status": "Reviewed"})
        draft = frappe.get_doc({
            "doctype": "Salary Slip", "employee": employee.name, "employee_name": employee.employee_name,
            "company": company, "posting_date": PAY_DATE, "start_date": START_DATE, "end_date": PAY_DATE,
            "currency": "VND", "exchange_rate": 1, "payroll_frequency": "Monthly",
            "total_working_days": 30, "payment_days": 30,
            "salary_structure": f"{TAG} Structure",
            "earnings": [{"salary_component": basic.name, "amount": float(BASIC_AMOUNT)}],
        })
        expected = calculate_salary_slip(draft)
        assert expected["status"] == "Ready", expected["blockers"]
        expected_by_type = {row["line_type"]: money(row["amount"]) for row in expected["lines"]}
        expected_employee = {
            "BHXH_EE": expected_by_type["BHXH_EE"],
            "BHYT_EE": expected_by_type["BHYT_EE"],
            "BHTN_EE": expected_by_type["BHTN_EE"],
            "PIT_WITHHOLDING": expected_by_type["PIT_WITHHOLDING"],
        }
        component_map = {
            "BHXH_EE": bxh.name, "BHYT_EE": byt.name,
            "BHTN_EE": btn.name, "PIT_WITHHOLDING": pitc.name,
        }
        for code, component in component_map.items():
            insert({
                "doctype": "VN Contribution Component", "company": company,
                "contribution_code": code, "salary_component": component,
                "effective_from": "2026-01-01", "mapping_status": "Released",
            })
        structure = frappe.get_doc({
            "doctype": "Salary Structure", "name": f"{TAG} Structure",
            "company": company, "is_active": "Yes", "currency": "VND",
            "payroll_frequency": "Monthly",
            "earnings": [{"salary_component": basic.name, "amount": float(BASIC_AMOUNT)}],
            "deductions": [
                {"salary_component": bxh.name, "amount": float(expected_employee["BHXH_EE"])},
                {"salary_component": byt.name, "amount": float(expected_employee["BHYT_EE"])},
                {"salary_component": btn.name, "amount": float(expected_employee["BHTN_EE"])},
                {"salary_component": pitc.name, "amount": float(expected_employee["PIT_WITHHOLDING"])},
            ],
        })
        structure.insert(ignore_permissions=True)
        structure.submit()
        assignment = insert({
            "doctype": "Salary Structure Assignment", "employee": employee.name,
            "salary_structure": structure.name, "from_date": START_DATE,
            "company": company, "currency": "VND", "base": float(BASIC_AMOUNT),
        })
        assignment.submit()
        payroll_payable = frappe.db.get_value("Company", company, "default_payroll_payable_account")
        assert payroll_payable, "Company needs default payroll payable account for controlled accrual preview"
        for role, code in [
            ("BHXH_PAYABLE", "3383"),
            ("BHYT_PAYABLE", "3384"),
            ("BHTN_PAYABLE", "3386"),
        ]:
            insert({
                "doctype": "VN COA Mapping", "company": company,
                "statutory_role": role, "statutory_code": code,
                "account": payroll_payable, "accounting_regime": "TT99_2025",
                "effective_from": "2026-01-01",
                "notes": f"{TAG} rollback-only UAT mapping",
            })
        slip = make_salary_slip(
            structure.name, employee=employee.name, posting_date=PAY_DATE,
            ignore_permissions=True,
        )
        slip.insert(ignore_permissions=True)
        actual_deductions = {row.salary_component: money(row.amount) for row in slip.deductions}
        for code, component in component_map.items():
            assert actual_deductions.get(component) == expected_employee[code], (
                code, actual_deductions.get(component), expected_employee[code]
            )
        slip.submit()
        slip.reload()
        evidence = frappe.get_all(
            "VN Payroll Calculation Line", filters={"salary_slip": slip.name},
            fields=["line_type", "amount", "snapshot_hash"], order_by="line_type asc",
        )
        assert evidence, "Salary Slip submit did not create VN payroll evidence"
        hashes = {row.snapshot_hash for row in evidence}
        assert len(hashes) == 1 and slip.vn_payroll_snapshot_hash in hashes, hashes
        recon = reconcile_salary_slip(slip.name)
        assert recon["status"] == "MATCH", recon
        accrual = employer_accrual_preview(company, START_DATE, PAY_DATE)
        assert accrual["configured"] is True, accrual
        assert not accrual["unmapped"], accrual
        assert accrual["read_only"] is True, accrual
        assert money(accrual["employer_contribution_total"]) == money(expected["employer_insurance"]), accrual
        assert slip.vn_payroll_compliance_status == "Ready"
        assert money(slip.vn_pit_calculated) == money(expected["pit"])
        assert money(slip.vn_employee_insurance_total) == money(expected["employee_insurance"])
        assert money(slip.vn_employer_insurance_total) == money(expected["employer_insurance"])
        during_counts = {
            "journal_entries": frappe.db.count("Journal Entry"),
            "gl_entries": frappe.db.count("GL Entry"),
            "submissions": frappe.db.count("VN Submission"),
        }
        assert during_counts == before_counts, (before_counts, during_counts)
        result = {
            "status": "PASS", "company": company, "period": [START_DATE, PAY_DATE],
            "gross_pay": money(slip.gross_pay), "total_deduction": money(slip.total_deduction),
            "net_pay": money(slip.net_pay), "pit": money(expected["pit"]),
            "employee_insurance": money(expected["employee_insurance"]),
            "employer_insurance": money(expected["employer_insurance"]),
            "reconciliation": recon["status"], "evidence_lines": len(evidence),
            "snapshot_hash": slip.vn_payroll_snapshot_hash,
            "accrual_lines": accrual["payable_lines"],
            "wage_region": {"name": wage.name, "code": wage.code, "minimum": wage.monthly_minimum_wage},
            "tax_profile": tax_profile.name, "social_profile": social_profile.name,
        }
        print("P2_UAT_RESULT=" + json.dumps(result, default=str, sort_keys=True))
        frappe.db.rollback()
        leftovers = {
            "settings": frappe.db.exists("VN Localization Settings", company),
            "employee": frappe.db.exists("Employee", {"employee_number": TAG}),
            "component": frappe.db.exists("Salary Component", f"{TAG} Basic"),
            "structure": frappe.db.exists("Salary Structure", f"{TAG} Structure"),
            "holiday": frappe.db.exists("Holiday List", f"{TAG} Holidays"),
            "evidence": frappe.db.count("VN Payroll Calculation Line", {"salary_slip": slip.name}),
        }
        assert not any(leftovers.values()), leftovers
        after_counts = {
            "journal_entries": frappe.db.count("Journal Entry"),
            "gl_entries": frappe.db.count("GL Entry"),
            "submissions": frappe.db.count("VN Submission"),
        }
        assert after_counts == before_counts, (before_counts, after_counts)
        rollback_result = {"leftovers": leftovers, "side_effect_counts": after_counts}
        print("P2_UAT_ROLLBACK=" + json.dumps(rollback_result, default=str, sort_keys=True))
    except Exception:
        frappe.db.rollback()
        raise
    finally:
        frappe.destroy()

if __name__ == "__main__":
    main()
