from __future__ import annotations

from erpnext_vietnam.einvoice.service import prepare_companion


def on_sales_invoice_submit(doc, method=None):
    # Local preparation only. Never submits to a provider or authority from a document hook.
    prepare_companion(doc.name, require_feature_enabled=True)
