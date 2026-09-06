from __future__ import annotations

import frappe


def _ensure(doctype: str, key: str, values: dict):
    if frappe.db.exists(doctype, key):
        return frappe.get_doc(doctype, key)
    doc = frappe.get_doc({"doctype": doctype, **values})
    doc.insert(ignore_permissions=True)
    return doc


def seed_p1_reference_data():
    instruments = [
        {"name": "48/2024/QH15", "instrument_number": "48/2024/QH15", "title": "Luật Thuế giá trị gia tăng", "issuer": "Quốc hội", "publication_date": "2024-11-26", "effective_from": "2025-07-01", "official_url": "https://vanban.chinhphu.vn/?docid=212476&pageid=27160", "legal_status": "Effective", "notes": "Base VAT law; resolve together with effective amendments."},
        {"name": "204/2025/QH15", "instrument_number": "204/2025/QH15", "title": "Nghị quyết về giảm thuế giá trị gia tăng", "issuer": "Quốc hội", "publication_date": "2025-06-17", "effective_from": "2025-07-01", "effective_to": "2026-12-31", "official_url": "https://vanban.chinhphu.vn/?classid=1&docid=214209&pageid=27160", "legal_status": "Effective"},
        {"name": "174/2025/NĐ-CP", "instrument_number": "174/2025/NĐ-CP", "title": "Quy định chính sách giảm thuế GTGT theo Nghị quyết 204/2025/QH15", "issuer": "Chính phủ", "publication_date": "2025-06-30", "effective_from": "2025-07-01", "effective_to": "2026-12-31", "official_url": "https://vanban.chinhphu.vn/?docid=214310&pageid=27160", "legal_status": "Effective"},
        {"name": "181/2025/NĐ-CP", "instrument_number": "181/2025/NĐ-CP", "title": "Quy định chi tiết thi hành một số điều của Luật Thuế giá trị gia tăng", "issuer": "Chính phủ", "publication_date": "2025-07-01", "effective_from": "2025-07-01", "official_url": "https://vanban.chinhphu.vn/?classid=1&docid=214336&pageid=27160&typegroupid=4", "legal_status": "Effective", "notes": "Base implementing decree; apply with effective amendments."},
        {"name": "69/2025/TT-BTC", "instrument_number": "69/2025/TT-BTC", "title": "Quy định chi tiết một số điều của Luật Thuế GTGT và hướng dẫn Nghị định 181/2025/NĐ-CP", "issuer": "Bộ Tài chính", "publication_date": "2025-07-01", "effective_from": "2025-07-01", "official_url": "https://vanban.chinhphu.vn/?docid=214417&pageid=27160", "legal_status": "Effective"},
        {"name": "149/2025/QH15", "instrument_number": "149/2025/QH15", "title": "Luật sửa đổi, bổ sung một số điều của Luật Thuế giá trị gia tăng", "issuer": "Quốc hội", "publication_date": "2025-12-11", "effective_from": "2026-01-01", "official_url": "https://vanban.chinhphu.vn/?classid=1&docid=216588&pageid=27160&typegroupid=3", "legal_status": "Effective", "notes": "Amends Law 48/2024/QH15."},
        {"name": "359/2025/NĐ-CP", "instrument_number": "359/2025/NĐ-CP", "title": "Sửa đổi, bổ sung Nghị định 181/2025/NĐ-CP", "issuer": "Chính phủ", "publication_date": "2025-12-31", "effective_from": "2026-01-01", "official_url": "https://vanban.chinhphu.vn/?classid=1&docid=216388&pageid=27160&typegroupid=4", "legal_status": "Effective", "notes": "Amends Decree 181/2025/NĐ-CP."},
        {"name": "09/2026/QH16", "instrument_number": "09/2026/QH16", "title": "Luật sửa đổi một số luật thuế, gồm Luật Thuế giá trị gia tăng", "issuer": "Quốc hội", "publication_date": "2026-04-24", "effective_from": "2026-04-24", "official_url": "https://vanban.chinhphu.vn/?docid=218095&pageid=27160&typegroupid=3", "legal_status": "Effective", "notes": "Further amends the VAT law."},
        {"name": "144/2026/NĐ-CP", "instrument_number": "144/2026/NĐ-CP", "title": "Sửa đổi, bổ sung Nghị định 181/2025/NĐ-CP đã được sửa đổi bởi Nghị định 359/2025/NĐ-CP", "issuer": "Chính phủ", "publication_date": "2026-05-05", "effective_from": "2026-06-20", "official_url": "https://vanban.chinhphu.vn/?docid=218020&pageid=27160&typegroupid=4", "legal_status": "Effective", "notes": "Further amends the VAT implementing decree chain."},
        {"name": "99/2025/TT-BTC", "instrument_number": "99/2025/TT-BTC", "title": "Hướng dẫn Chế độ kế toán doanh nghiệp", "issuer": "Bộ Tài chính", "publication_date": "2025-10-27", "effective_from": "2026-01-01", "official_url": "https://www.mof.gov.vn/tin-tuc-tai-chinh/tin-chinh-sach-tai-chinh/quy-dinh-moi-ve-che-do-ke-toan-doanh-nghiep", "legal_status": "Effective"},
    ]
    for row in instruments:
        name = row.pop("name")
        _ensure("VN Legal Instrument", name, row)

    _ensure("VN Rule Set", "VAT-2025-2026-V1", {"code": "VAT-2025-2026-V1", "title": "Vietnam VAT baseline and temporary reduction 2025-2026", "effective_from": "2025-07-01", "effective_to": "2026-12-31", "rule_status": "Released", "notes": "Reference legal dataset; does not auto-classify Items."})

    if not frappe.db.exists("VN Rate Rule", {"code": "VAT.TEMP_REDUCTION_RATE", "effective_from": "2025-07-01", "rule_status": "Released"}):
        frappe.get_doc({"doctype": "VN Rate Rule", "rule_set": "VAT-2025-2026-V1", "code": "VAT.TEMP_REDUCTION_RATE", "value_type": "Decimal", "decimal_value": 8, "unit": "%", "effective_from": "2025-07-01", "effective_to": "2026-12-31", "priority": 100, "rule_status": "Released", "legal_instrument": "204/2025/QH15", "legal_reference_detail": "Article 1-2"}).insert(ignore_permissions=True)

    classifications = [
        ("VAT-NON-TAXABLE", "Không chịu thuế GTGT", "NON_TAXABLE", 0, 0, "48/2024/QH15", "Article 5 (as amended)"),
        ("VAT-ZERO-0", "Thuế suất GTGT 0%", "ZERO_RATE_0", 0, 0, "48/2024/QH15", "Article 9 (as amended)"),
        ("VAT-REDUCED-5", "Thuế suất GTGT 5%", "REDUCED_5", 5, 0, "48/2024/QH15", "Article 9 (as amended)"),
        ("VAT-STANDARD-10", "Thuế suất GTGT 10%", "STANDARD_10", 10, 0, "48/2024/QH15", "Article 9 (as amended)"),
        ("VAT-STANDARD-10-TEMP-ELIGIBLE", "Thuế suất 10% - đủ điều kiện giảm tạm thời", "STANDARD_10", 10, 1, "204/2025/QH15", "Article 1"),
    ]
    for code, title, treatment, rate, eligible, instrument, ref in classifications:
        if frappe.db.exists("VN VAT Classification", code):
            continue
        frappe.get_doc({"doctype": "VN VAT Classification", "code": code, "title": title, "classification_status": "Released", "treatment": treatment, "statutory_rate": rate, "temporary_reduction_eligible": eligible, "effective_from": "2025-07-01", "rule_set": "VAT-2025-2026-V1", "legal_instrument": instrument, "legal_reference_detail": ref, "notes": "Generic reference classification. Assignment to an Item requires accountant review; domain presets never auto-assign legal treatment."}).insert(ignore_permissions=True)
