from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from erpnext_vietnam.declarations.canonical import payload_hash

SCHEMA_VERSION = "VN-EINVOICE-CANONICAL-2026-01"
LEGAL_SOURCE = "254/2026/ND-CP + 91/2026/TT-BTC"


def _d(value) -> Decimal:
    return Decimal(str(value or 0))


def _money(value, precision: int = 0) -> Decimal:
    quantum = Decimal("1") if precision == 0 else Decimal("1").scaleb(-precision)
    return _d(value).quantize(quantum, rounding=ROUND_HALF_UP)


def build_canonical_invoice(source: dict[str, Any]) -> dict[str, Any]:
    currency = source.get("currency") or "VND"
    precision = 0 if currency == "VND" else int(source.get("currency_precision") or 2)
    missing: list[str] = []
    warnings: list[str] = []

    seller = dict(source.get("seller") or {})
    buyer = dict(source.get("buyer") or {})
    for side, values in (("seller", seller), ("buyer", buyer)):
        if not values.get("legal_name"):
            missing.append(f"{side}.legal_name")
        if not values.get("tax_id"):
            missing.append(f"{side}.tax_id")

    lines = []
    net_total = Decimal("0")
    vat_total = Decimal("0")
    for raw in source.get("lines") or []:
        idx = int(raw.get("idx") or len(lines) + 1)
        treatment = raw.get("vat_treatment")
        snapshot = raw.get("vat_snapshot_hash")
        rate = _d(raw.get("vat_rate"))
        net = _money(raw.get("net_amount"), precision)
        vat = _money(net * rate / Decimal("100"), precision)
        if not treatment:
            missing.append(f"line[{idx}].vat_treatment")
        if not snapshot:
            missing.append(f"line[{idx}].vat_snapshot_hash")
        if treatment == "NON_TAXABLE" and rate != 0:
            missing.append(f"line[{idx}].non_taxable_rate_must_be_zero")
        lines.append({
            "idx": idx,
            "item_code": raw.get("item_code"),
            "description": raw.get("description"),
            "qty": _d(raw.get("qty")),
            "uom": raw.get("uom"),
            "net_amount": net,
            "vat_classification": raw.get("vat_classification"),
            "vat_treatment": treatment,
            "vat_rate": rate,
            "vat_amount": vat,
            "vat_snapshot_hash": snapshot,
            "vat_reporting_category": raw.get("vat_reporting_category"),
        })
        net_total += net
        vat_total += vat

    native_net = _money(source.get("net_total"), precision)
    native_tax_raw = source.get("native_vat_total")
    if native_tax_raw is None:
        missing.append("native_vat_total_evidence")
    native_tax = _money(native_tax_raw, precision)
    native_grand = _money(source.get("grand_total"), precision)
    if _money(net_total, precision) != native_net:
        missing.append("net_total_reconciliation")
    if _money(vat_total, precision) != native_tax:
        missing.append("vat_total_reconciliation")
    if _money(native_net + native_tax, precision) != native_grand:
        warnings.append("Native grand total includes amounts outside canonical net+VAT or does not reconcile exactly.")

    payload = {
        "schema": SCHEMA_VERSION,
        "legal_source": LEGAL_SOURCE,
        "source": source.get("source") or {},
        "seller": seller,
        "buyer": buyer,
        "invoice_type": source.get("invoice_type") or "VAT_INVOICE",
        "currency": currency,
        "exchange_rate": _d(source.get("exchange_rate") or 1),
        "lines": lines,
        "net_total": native_net,
        "vat_total": native_tax,
        "grand_total": native_grand,
        "missing_required": sorted(set(missing)),
        "warnings": sorted(set(warnings)),
    }
    payload["ready"] = not payload["missing_required"]
    payload["payload_hash"] = payload_hash({k: v for k, v in payload.items() if k != "payload_hash"})
    return payload
