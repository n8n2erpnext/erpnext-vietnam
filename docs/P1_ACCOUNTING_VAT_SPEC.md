# P1 — Accounting + VAT

Status: implementation checkpoint P1A

## Boundary

ERPNext remains the transaction, tax calculation and GL engine. `erpnext_vietnam` provides legal classification, effective-dated metadata, Company-specific statutory account mapping, validation and immutable evidence hashes. No handler posts GL entries or replaces ERPNext tax calculation.

## Accounting mapping

`VN COA Mapping` maps canonical semantic roles (for example `VAT_OUTPUT_PAYABLE`) to the actual ERPNext `Account` of one Company and accounting regime. Suggested TT99 account numbers are metadata only and are never referenced by transaction handlers. Overlapping mappings for the same Company/role/regime are rejected.

## VAT treatments

The legal layer keeps distinct treatments: `NON_TAXABLE`, `ZERO_RATE_0`, `REDUCED_5`, `TEMP_REDUCED_8`, `STANDARD_10`. A generic `STANDARD_10` classification may be explicitly marked eligible for a temporary reduction; the actual temporary rate/effective dates are resolved from released `VN Rate Rule` data, not hard-coded in invoice handlers.

## Native ERPNext integration

Items receive an optional `VN VAT Classification` link. Sales/Purchase Invoice Item rows snapshot the resolved legal treatment, rate and SHA-256 evidence. If the Company's mapped VAT control account is present in ERPNext's native `item_tax_rate`, P1 validates that native Item Tax Template rate against the resolved legal rate. Mixed-rate invoices remain native ERPNext invoices.

Purchase Invoice rows additionally carry input-VAT deduction status, deductible ratio and evidence reference. P1A validates ratio bounds and preserves evidence fields but does not yet calculate a statutory declaration.

## Rollout safety

The app is inert for a Company until `VN Localization Settings` exists and VAT is configured. `VAT Validation Mode` supports Off, Advisory and Strict; missing classifications are only blocking in Strict mode. Selecting an invalid/expired/released classification or a contradictory native VAT rate is always rejected because it is explicit evidence, not a heuristic.

## Reference legal seed

P1A seeds versioned, globally inert reference records for the VAT legal chain (Law 48/2024/QH15 and effective amendments, Decree 181/2025/NĐ-CP and effective amendments, Circular 69/2025/TT-BTC), Resolution 204/2025/QH15 + Decree 174/2025/NĐ-CP for the temporary reduction, and Circular 99/2025/TT-BTC for accounting. The temporary 8% rule is effective 2025-07-01 through 2026-12-31. Generic VAT classification templates are never auto-assigned to Items.

The complete TT99 Appendix II Chart of Accounts import remains P1B and must be verified against the Appendix II source before release. Domain presets may recommend mappings but never infer tax treatment automatically.
