from __future__ import annotations

import io
import json
import re
import zipfile
from decimal import Decimal
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

from erpnext_vietnam.declarations.canonical import canonical_json, payload_hash

REVIEW_SCHEMA = "vn-statutory-review-v1"
_FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


class ReviewExportError(ValueError):
    pass


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (dict, list, tuple)):
        return canonical_json(value)
    return str(value)


def _natural_key(value: str):
    parts = re.split(r"(\d+)", str(value))
    return tuple(int(part) if part.isdigit() else part.lower() for part in parts)


def _adapter_without_embedded_hash(adapter: dict) -> dict:
    return {key: value for key, value in adapter.items() if key != "payload_hash"}


def validate_adapter_payload(adapter: dict) -> None:
    if not isinstance(adapter, dict):
        raise ReviewExportError("Adapter payload must be an object")
    if adapter.get("ready") is not True:
        raise ReviewExportError("Adapter must be Ready before an export package can be generated")
    if adapter.get("missing_required"):
        raise ReviewExportError("Ready adapter cannot contain missing_required entries")
    embedded = adapter.get("payload_hash")
    if embedded and embedded != payload_hash(_adapter_without_embedded_hash(adapter)):
        raise ReviewExportError("Adapter embedded payload hash does not match its content")
    for field in ("form_code", "adapter_version", "legal_source"):
        if not adapter.get(field):
            raise ReviewExportError(f"Adapter payload is missing {field}")


def _metadata(adapter: dict, metadata: dict | None) -> dict:
    data = dict(metadata or {})
    data.setdefault("review_schema", REVIEW_SCHEMA)
    data.setdefault("form_code", adapter["form_code"])
    data.setdefault("adapter_version", adapter["adapter_version"])
    data.setdefault("legal_source", adapter["legal_source"])
    data.setdefault("adapter_payload_hash", adapter.get("payload_hash") or payload_hash(_adapter_without_embedded_hash(adapter)))
    return data


def build_review_xml(adapter: dict, metadata: dict | None = None) -> bytes:
    validate_adapter_payload(adapter)
    meta = _metadata(adapter, metadata)
    root = ET.Element("VNStatutoryReviewPackage", {"schema": REVIEW_SCHEMA})
    meta_el = ET.SubElement(root, "Metadata")
    for key in sorted(meta, key=_natural_key):
        el = ET.SubElement(meta_el, "Field", {"name": str(key)})
        el.text = _text(meta[key])

    indicators_el = ET.SubElement(root, "Indicators")
    for key in sorted(adapter.get("indicators") or {}, key=_natural_key):
        el = ET.SubElement(indicators_el, "Indicator", {"code": str(key)})
        el.text = _text(adapter["indicators"][key])

    rows_el = ET.SubElement(root, "Rows")
    for index, row in enumerate(adapter.get("rows") or [], start=1):
        row_el = ET.SubElement(rows_el, "Row", {"index": str(index)})
        columns = row.get("columns") if isinstance(row, dict) else None
        if isinstance(columns, dict):
            for key in sorted(columns, key=_natural_key):
                el = ET.SubElement(row_el, "Column", {"code": str(key)})
                el.text = _text(columns[key])
        extras = {key: value for key, value in (row or {}).items() if key != "columns"}
        if extras:
            ET.SubElement(row_el, "Evidence").text = canonical_json(extras)

    issues_el = ET.SubElement(root, "ReviewNotes")
    for kind, values in (("warning", adapter.get("warnings") or []), ("missing", adapter.get("missing_required") or [])):
        for value in values:
            ET.SubElement(issues_el, "Note", {"type": kind}).text = _text(value)

    sources_el = ET.SubElement(root, "SourceReferences")
    for source in adapter.get("source_refs") or []:
        ET.SubElement(sources_el, "Source").text = canonical_json(source)

    return ET.tostring(root, encoding="utf-8", xml_declaration=True, short_empty_elements=True)


def _xlsx_col(number: int) -> str:
    value = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        value = chr(65 + remainder) + value
    return value


def _cell_xml(row: int, col: int, value) -> str:
    ref = f"{_xlsx_col(col)}{row}"
    if value is None:
        return f'<c r="{ref}" t="inlineStr"><is><t></t></is></c>'
    if isinstance(value, bool):
        return f'<c r="{ref}" t="b"><v>{1 if value else 0}</v></c>'
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        return f'<c r="{ref}"><v>{escape(_text(value))}</v></c>'
    text = escape(_text(value))
    return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'


def _sheet_xml(rows: list[list]) -> bytes:
    body = []
    for row_index, values in enumerate(rows, start=1):
        cells = "".join(_cell_xml(row_index, col_index, value) for col_index, value in enumerate(values, start=1))
        body.append(f'<row r="{row_index}">{cells}</row>')
    xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' \
          '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' \
          '<sheetData>' + "".join(body) + '</sheetData></worksheet>'
    return xml.encode("utf-8")


def _xlsx_rows(adapter: dict, metadata: dict | None) -> list[tuple[str, list[list]]]:
    meta = _metadata(adapter, metadata)
    summary = [["Field", "Value"]] + [[key, meta[key]] for key in sorted(meta, key=_natural_key)]
    indicators = [["Indicator", "Value"]] + [[key, adapter.get("indicators", {}).get(key)] for key in sorted(adapter.get("indicators") or {}, key=_natural_key)]

    source_rows = adapter.get("rows") or []
    column_keys = sorted({str(key) for row in source_rows for key in ((row.get("columns") or {}).keys() if isinstance(row, dict) else [])}, key=_natural_key)
    rows = [["Row", *column_keys, "Evidence JSON"]]
    for index, row in enumerate(source_rows, start=1):
        columns = row.get("columns") or {}
        evidence = {key: value for key, value in row.items() if key != "columns"}
        rows.append([index, *[columns.get(key) for key in column_keys], canonical_json(evidence) if evidence else ""])

    issues = [["Type", "Message"]]
    issues.extend([["Warning", value] for value in adapter.get("warnings") or []])
    issues.extend([["Missing", value] for value in adapter.get("missing_required") or []])
    sources = [["Source JSON"]] + [[canonical_json(value)] for value in adapter.get("source_refs") or []]
    return [("Summary", summary), ("Indicators", indicators), ("Rows", rows), ("Review Notes", issues), ("Sources", sources)]


def _zip_write(archive: zipfile.ZipFile, name: str, content: bytes) -> None:
    info = zipfile.ZipInfo(name, _FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o600 << 16
    archive.writestr(info, content)


def build_review_xlsx(adapter: dict, metadata: dict | None = None) -> bytes:
    validate_adapter_payload(adapter)
    sheets = _xlsx_rows(adapter, metadata)
    workbook_sheets = "".join(
        f'<sheet name="{escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
        for index, (name, _) in enumerate(sheets, start=1)
    )
    workbook = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets>{workbook_sheets}</sheets></workbook>').encode("utf-8")
    rels = "".join(
        f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
        for index in range(1, len(sheets) + 1)
    )
    workbook_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'{rels}</Relationships>').encode("utf-8")
    root_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>').encode("utf-8")
    overrides = ''.join(
        f'<Override PartName="/xl/worksheets/sheet{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for index in range(1, len(sheets) + 1)
    )
    content_types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        f'{overrides}</Types>').encode("utf-8")

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        _zip_write(archive, "[Content_Types].xml", content_types)
        _zip_write(archive, "_rels/.rels", root_rels)
        _zip_write(archive, "xl/workbook.xml", workbook)
        _zip_write(archive, "xl/_rels/workbook.xml.rels", workbook_rels)
        for index, (_, rows) in enumerate(sheets, start=1):
            _zip_write(archive, f"xl/worksheets/sheet{index}.xml", _sheet_xml(rows))
    return output.getvalue()


def build_review_export(adapter: dict, export_format: str, metadata: dict | None = None) -> bytes:
    fmt = (export_format or "").strip().lower()
    if fmt == "xml":
        return build_review_xml(adapter, metadata)
    if fmt == "xlsx":
        return build_review_xlsx(adapter, metadata)
    raise ReviewExportError("Supported review export formats are XML and XLSX")


def export_filename(form_code: str, document_name: str, export_format: str) -> str:
    safe_form = re.sub(r"[^A-Za-z0-9._-]+", "-", form_code).strip("-") or "VN-Form"
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", document_name).strip("-") or "document"
    return f"{safe_form}-{safe_name}-review.{export_format.lower()}"


def export_mimetype(export_format: str) -> str:
    fmt = export_format.lower()
    if fmt == "xml":
        return "application/xml"
    if fmt == "xlsx":
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    raise ReviewExportError("Unsupported review export format")
