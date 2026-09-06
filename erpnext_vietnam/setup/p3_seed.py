from __future__ import annotations

import frappe


CIRCULAR_89_SOURCE_SHA256 = "952c45ffc0f10bfc176bd9ae6b3d204fd3a034294ee270278957b9c11e1471dc"
CIRCULAR_89_URL = "https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/7/89-btc.signed.pdf"


def seed_p3_reference_data():
    number = "89/2026/TT-BTC"
    if frappe.db.exists("VN Legal Instrument", number):
        return
    frappe.get_doc({
        "doctype": "VN Legal Instrument",
        "instrument_number": number,
        "title": "Quy định chi tiết một số điều của Luật Quản lý thuế và Nghị định 252/2026/NĐ-CP",
        "issuer": "Bộ Tài chính",
        "publication_date": "2026-06-30",
        "effective_from": "2026-07-01",
        "official_url": CIRCULAR_89_URL,
        "source_sha256": CIRCULAR_89_SOURCE_SHA256,
        "legal_status": "Effective",
        "notes": "P3 tax-declaration source baseline. Exact government format adapters remain separately versioned and reviewed.",
    }).insert(ignore_permissions=True)
