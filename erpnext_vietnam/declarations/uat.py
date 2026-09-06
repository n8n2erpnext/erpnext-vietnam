from __future__ import annotations

import json
from io import BytesIO
from xml.etree import ElementTree as ET
import zipfile

import frappe
from frappe.utils import getdate

from erpnext_vietnam.declarations.adapters.base import AdapterResult
from erpnext_vietnam.declarations.canonical import canonical_json
from erpnext_vietnam.declarations.exporters.review import build_review_export
from erpnext_vietnam.declarations.service import _load_ready_adapter_document


def _count(doctype: str) -> int:
    return frappe.db.count(doctype)


def _ready_adapter(form_code: str) -> dict:
    return AdapterResult(
        form_code=form_code,
        adapter_version="p3d-uat-v1",
        legal_source="synthetic-rollback-uat",
        indicators={"uat": "reviewed"},
        rows=[],
        missing_required=[],
        warnings=["Synthetic rollback-only engineering UAT"],
        source_refs=[{"source": "synthetic"}],
    ).as_dict()


def _assert_export_bytes(adapter: dict) -> dict:
    xml = build_review_export(adapter, "xml", {"document_name": "P3D-UAT"})
    xlsx = build_review_export(adapter, "xlsx", {"document_name": "P3D-UAT"})
    root = ET.fromstring(xml)
    if root.tag != "VNStatutoryReviewPackage":
        raise AssertionError("Unexpected review XML root")
    with zipfile.ZipFile(BytesIO(xlsx)) as archive:
        names = set(archive.namelist())
        if "xl/workbook.xml" not in names or "xl/worksheets/sheet1.xml" not in names:
            raise AssertionError("Review XLSX package is incomplete")
    return {"xml_bytes": len(xml), "xlsx_bytes": len(xlsx)}


def run_review_export_uat(company: str) -> dict:
    if not frappe.db.exists("Company", company):
        raise ValueError(f"Company does not exist: {company}")
    tracked = ("GL Entry", "Journal Entry", "VN Submission", "VN Tax Declaration", "VN Social Insurance Export")
    before = {doctype: _count(doctype) for doctype in tracked}
    created = {}
    result = {}
    try:
        tax_adapter = _ready_adapter("01/GTGT")
        tax_doc = frappe.get_doc({
            "doctype": "VN Tax Declaration",
            "company": company,
            "declaration_type": "01_GTGT",
            "period_type": "Quarter",
            "from_date": getdate("2026-07-01"),
            "to_date": getdate("2026-09-30"),
            "status": "Prepared",
            "schema_version": "uat-v1",
            "legal_instrument": "89/2026/TT-BTC",
            "calculation_snapshot_json": "{}",
            "declaration_json": canonical_json({"source_documents": [], "uat": True}),
            "adapter_payload_json": canonical_json(tax_adapter),
            "warning_json": "[]",
        }).insert(ignore_permissions=True)
        created["tax"] = tax_doc.name

        si_adapter = _ready_adapter("TK3-TS")
        si_doc = frappe.get_doc({
            "doctype": "VN Social Insurance Export",
            "company": company,
            "export_type": "TK3_TS",
            "subject_doctype": "Company",
            "subject_name": company,
            "from_date": getdate("2026-09-06"),
            "to_date": getdate("2026-09-06"),
            "status": "Prepared",
            "schema_version": "uat-v1",
            "canonical_payload_json": canonical_json({"company": company, "uat": True}),
            "adapter_payload_json": canonical_json(si_adapter),
            "warning_json": "[]",
        }).insert(ignore_permissions=True)
        created["social_insurance"] = si_doc.name

        loaded_tax, loaded_tax_adapter = _load_ready_adapter_document("VN Tax Declaration", tax_doc.name)
        loaded_si, loaded_si_adapter = _load_ready_adapter_document("VN Social Insurance Export", si_doc.name)
        result["tax"] = {"name": loaded_tax.name, **_assert_export_bytes(loaded_tax_adapter)}
        result["social_insurance"] = {"name": loaded_si.name, **_assert_export_bytes(loaded_si_adapter)}

        during = {doctype: _count(doctype) for doctype in tracked}
        for doctype in ("GL Entry", "Journal Entry", "VN Submission"):
            if during[doctype] != before[doctype]:
                raise AssertionError(f"Unexpected side effect in {doctype}")
        if during["VN Tax Declaration"] != before["VN Tax Declaration"] + 1:
            raise AssertionError("Expected exactly one temporary VN Tax Declaration")
        if during["VN Social Insurance Export"] != before["VN Social Insurance Export"] + 1:
            raise AssertionError("Expected exactly one temporary VN Social Insurance Export")
        result["during_counts"] = during
    finally:
        frappe.db.rollback()

    after = {doctype: _count(doctype) for doctype in tracked}
    if after != before:
        raise AssertionError({"rollback_failed": {"before": before, "after": after}, "created": created})
    result.update({"before_counts": before, "after_counts": after, "rollback_clean": True})
    return result
