from __future__ import annotations

import frappe


def _ensure(doctype: str, name: str, values: dict):
    if frappe.db.exists(doctype, name):
        return frappe.get_doc(doctype, name)
    return frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)


def _ensure_rate(code: str, effective_from: str, value: float, unit: str, instrument: str, ref: str, effective_to: str | None = None):
    filters = {"code": code, "effective_from": effective_from, "rule_status": "Released"}
    if frappe.db.exists("VN Rate Rule", filters):
        return
    frappe.get_doc({
        "doctype": "VN Rate Rule", "rule_set": "PAYROLL-VN-2026-V1", "code": code,
        "value_type": "Decimal", "decimal_value": value, "unit": unit,
        "effective_from": effective_from, "effective_to": effective_to,
        "priority": 100, "rule_status": "Released", "legal_instrument": instrument,
        "legal_reference_detail": ref,
    }).insert(ignore_permissions=True)


def seed_p2_reference_data():
    instruments = [
        ("109/2025/QH15", "Luật Thuế thu nhập cá nhân", "Quốc hội", "2025-12-10", "2026-07-01", "https://vanban.chinhphu.vn/?classid=1&docid=216495&pageid=27160", "Salary/wage provisions apply from tax period 2026."),
        ("110/2025/UBTVQH15", "Nghị quyết điều chỉnh mức giảm trừ gia cảnh thuế TNCN", "Ủy ban Thường vụ Quốc hội", "2025-10-17", "2026-01-01", "https://vanban.chinhphu.vn/?docid=215927&pageid=27160", None),
        ("41/2024/QH15", "Luật Bảo hiểm xã hội", "Quốc hội", "2024-06-29", "2025-07-01", "https://vanban.chinhphu.vn/?docid=211199&pageid=27160", None),
        ("158/2025/NĐ-CP", "Quy định chi tiết bảo hiểm xã hội bắt buộc", "Chính phủ", "2025-06-25", "2025-07-01", "https://vanban.chinhphu.vn/?classid=1&docid=214189&pageid=27160", None),
        ("188/2025/NĐ-CP", "Quy định chi tiết và hướng dẫn Luật Bảo hiểm y tế", "Chính phủ", "2025-07-01", "2025-08-15", "https://vanban.chinhphu.vn/?classid=1&docid=214515&pageid=27160", None),
        ("74/2025/QH15", "Luật Việc làm", "Quốc hội", "2025-06-16", "2026-01-01", "https://vanban.chinhphu.vn/?docid=214560&pageid=27160", None),
        ("374/2025/NĐ-CP", "Quy định chi tiết một số điều của Luật Việc làm về bảo hiểm thất nghiệp", "Chính phủ", "2025-12-31", "2026-01-01", "https://vanban.chinhphu.vn/?docid=216493&pageid=27160", None),
        ("293/2025/NĐ-CP", "Quy định mức lương tối thiểu đối với người lao động làm việc theo hợp đồng lao động", "Chính phủ", "2025-11-10", "2026-01-01", "https://vanban.chinhphu.vn/?classid=1&docid=215832&pageid=27160", None),
        ("58/2020/NĐ-CP", "Mức đóng vào Quỹ bảo hiểm tai nạn lao động, bệnh nghề nghiệp", "Chính phủ", "2020-05-27", "2020-07-15", "https://vanban.chinhphu.vn/?docid=200108&pageid=27160", "Apply together with amendments in Decree 158/2025/NĐ-CP."),
        ("161/2026/NĐ-CP", "Mức lương cơ sở và chế độ tiền thưởng", "Chính phủ", "2026-05-15", "2026-07-01", "https://vanban.chinhphu.vn/?classid=1&docid=218107&pageid=27160", "During the transition, the BHXH reference level equals the base salary."),
    ]
    for number, title, issuer, pub, effective, url, notes in instruments:
        _ensure("VN Legal Instrument", number, {
            "instrument_number": number, "title": title, "issuer": issuer,
            "publication_date": pub, "effective_from": effective, "official_url": url,
            "legal_status": "Effective", "notes": notes,
        })

    _ensure("VN Rule Set", "PAYROLL-VN-2026-V1", {
        "code": "PAYROLL-VN-2026-V1", "title": "Vietnam payroll PIT and compulsory insurance 2026",
        "effective_from": "2026-01-01", "rule_status": "Released",
        "notes": "Effective-dated reference rules. Salary Components and employee profiles require explicit review before payroll evidence activates.",
    })

    for code, start, value, unit, inst, ref, end in [
        ("PIT.PERSONAL_DEDUCTION_MONTHLY", "2026-01-01", 15500000, "VND/month", "110/2025/UBTVQH15", "Article 1", None),
        ("PIT.DEPENDENT_DEDUCTION_MONTHLY", "2026-01-01", 6200000, "VND/month", "110/2025/UBTVQH15", "Article 1", None),
        ("PIT.NONRESIDENT_SALARY_RATE", "2026-01-01", 20, "%", "109/2025/QH15", "Salary/wage provisions for tax period 2026", None),
        ("SI.REFERENCE_LEVEL", "2026-01-01", 2340000, "VND/month", "41/2024/QH15", "Transition: reference level equals base salary while base salary remains in force", "2026-06-30"),
        ("SI.REFERENCE_LEVEL", "2026-07-01", 2530000, "VND/month", "161/2026/NĐ-CP", "Base salary 2,530,000 VND from 2026-07-01; reference-level transition", None),
        ("SI.BHXH_EE_RATE", "2026-01-01", 8, "%", "41/2024/QH15", "Article 33", None),
        ("SI.BHXH_ER_RATE", "2026-01-01", 17, "%", "41/2024/QH15", "Article 34: 3% sickness/maternity + 14% retirement/survivorship", None),
        ("SI.BHYT_EE_RATE", "2026-01-01", 1.5, "%", "188/2025/NĐ-CP", "Ordinary employee share", None),
        ("SI.BHYT_ER_RATE", "2026-01-01", 3, "%", "188/2025/NĐ-CP", "Ordinary employer share", None),
        ("SI.BHTN_EE_RATE", "2026-01-01", 1, "%", "374/2025/NĐ-CP", "Ordinary employee contribution", None),
        ("SI.BHTN_ER_RATE", "2026-01-01", 1, "%", "374/2025/NĐ-CP", "Ordinary employer contribution", None),
        ("SI.OAI_ER_RATE", "2026-01-01", 0.5, "%", "58/2020/NĐ-CP", "Ordinary rate as amended by Decree 158/2025/NĐ-CP", None),
    ]:
        _ensure_rate(code, start, value, unit, inst, ref, end)

    brackets = [
        (1, 0, 10000000, 5), (2, 10000000, 30000000, 10),
        (3, 30000000, 60000000, 20), (4, 60000000, 100000000, 30),
        (5, 100000000, None, 35),
    ]
    for seq, lower, upper, rate in brackets:
        code = f"PIT-2026-M-{seq}"
        if not frappe.db.exists("VN PIT Bracket", code):
            frappe.get_doc({
                "doctype": "VN PIT Bracket", "code": code, "residency": "Resident",
                "period_basis": "Monthly", "sequence": seq, "lower_bound": lower,
                "upper_bound": upper, "rate_percent": rate, "currency": "VND",
                "effective_from": "2026-01-01", "rule_set": "PAYROLL-VN-2026-V1",
                "legal_instrument": "109/2025/QH15", "legal_reference_detail": "Article 9; applies to tax period 2026",
                "rule_status": "Released",
            }).insert(ignore_permissions=True)

    for code, name, monthly, hourly in [
        ("REGION-I-2026", "Vùng I", 5310000, 25500),
        ("REGION-II-2026", "Vùng II", 4730000, 22700),
        ("REGION-III-2026", "Vùng III", 4140000, 20000),
        ("REGION-IV-2026", "Vùng IV", 3700000, 17800),
    ]:
        if not frappe.db.exists("VN Wage Region", code):
            frappe.get_doc({
                "doctype": "VN Wage Region", "code": code, "region_name": name,
                "monthly_minimum_wage": monthly, "hourly_minimum_wage": hourly,
                "currency": "VND", "effective_from": "2026-01-01",
                "legal_instrument": "293/2025/NĐ-CP", "legal_reference_detail": "Article 3 and Appendix",
                "reference_status": "Released",
            }).insert(ignore_permissions=True)
