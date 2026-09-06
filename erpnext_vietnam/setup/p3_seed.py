from __future__ import annotations

import frappe


CIRCULAR_89_SOURCE_SHA256 = "952c45ffc0f10bfc176bd9ae6b3d204fd3a034294ee270278957b9c11e1471dc"
CIRCULAR_89_URL = "https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/7/89-btc.signed.pdf"
REPORTING_RULE_SET = "TAX-DECL-TT89-2026-V1"


def _ensure(doctype: str, name: str, values: dict):
    if frappe.db.exists(doctype, name):
        return frappe.get_doc(doctype, name)
    return frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)


def seed_p3_reference_data():
    number = "89/2026/TT-BTC"
    _ensure("VN Legal Instrument", number, {
        "instrument_number": number,
        "title": "Quy định chi tiết một số điều của Luật Quản lý thuế và Nghị định 252/2026/NĐ-CP",
        "issuer": "Bộ Tài chính",
        "publication_date": "2026-06-30",
        "effective_from": "2026-07-01",
        "official_url": CIRCULAR_89_URL,
        "source_sha256": CIRCULAR_89_SOURCE_SHA256,
        "legal_status": "Effective",
        "notes": "P3 tax-declaration source baseline; government-format adapters are separately versioned.",
    })
    _ensure("VN Rule Set", REPORTING_RULE_SET, {
        "code": REPORTING_RULE_SET,
        "title": "TT89/2026 statutory reporting taxonomy",
        "effective_from": "2026-07-01",
        "rule_status": "Released",
        "notes": "Reporting buckets are separate from VAT treatment/rate semantics and never auto-classify transactions.",
    })

    categories = [
        ("TT89-OUT-NON-TAXABLE", "01/GTGT [26] - Không chịu thuế GTGT", "Output", "26", None, None, None, "NON_TAXABLE", 0),
        ("TT89-OUT-ZERO", "01/GTGT [29] - Thuế suất 0%", "Output", "29", None, None, None, "ZERO_RATE_0", 0),
        ("TT89-OUT-FIVE", "01/GTGT [30]/[31] - Thuế suất 5%", "Output", "30", "31", None, None, "REDUCED_5", 0),
        ("TT89-OUT-TEN", "01/GTGT [32]/[33] - Thuế suất 10%", "Output", "32", "33", None, None, "STANDARD_10", 0),
        ("TT89-OUT-TEMP-EIGHT", "01/GTGT [32]/[33] - Giảm tạm thời 8%", "Output", "32", "33", None, None, "TEMP_REDUCED_8", 1),
        ("TT89-OUT-NOT-DECLARED", "01/GTGT [32a] - Không phải kê khai, tính thuế", "Output", "32a", None, None, None, "ANY_REVIEW", 0),
        ("TT89-OUT-NOT-IN-TAX-BASE", "01/GTGT [32b] - Không tính vào giá tính thuế", "Output", "32b", None, None, None, "ANY_REVIEW", 0),
        ("TT89-OUT-OUTSIDE-SCOPE", "01/GTGT [34a] - Ngoài phạm vi điều chỉnh VAT", "Output", "34a", None, None, None, "ANY_REVIEW", 0),
        ("TT89-IN-DOMESTIC", "01/GTGT [23]/[24] - Mua vào trong nước", "Input", "23", "24", None, None, "ANY_REVIEW", 0),
        ("TT89-IN-IMPORTED", "01/GTGT [23]/[24], trong đó [23a]/[24a] nhập khẩu", "Input", "23", "24", "23a", "24a", "ANY_REVIEW", 0),
    ]
    for code, title, direction, vi, ti, svi, sti, constraint, annex in categories:
        _ensure("VN VAT Reporting Category", code, {
            "code": code, "title": title, "reporting_status": "Released", "direction": direction,
            "value_indicator": vi, "tax_indicator": ti, "secondary_value_indicator": svi,
            "secondary_tax_indicator": sti, "treatment_constraint": constraint,
            "requires_reduction_annex": annex, "effective_from": "2026-07-01",
            "rule_set": REPORTING_RULE_SET, "legal_instrument": number,
            "legal_reference_detail": "Phụ lục I - Mẫu 01/GTGT",
            "notes": "Explicit statutory reporting category; assignment requires accountant review.",
        })
