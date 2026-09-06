# LightBI reference integration

This document is an integration example only. `erpnext_vietnam` has no runtime dependency on LightBI and contains no LightBI-specific code.

Example flow:

```text
LightBI Distribution / Licensing / Sales
        -> generic ERPNext commercial-document ingestion
        -> ERPNext GL / receivable / payment truth
        -> erpnext_vietnam statutory classification
        -> VAT / PIT / payroll / BHXH evidence
        -> declarations / future compliance submissions
        -> generic governed read API
        -> LightBI analytics
```

The same contracts must work unchanged for e-commerce, POS, CRM, hospitality, healthcare, manufacturing and other clients.
