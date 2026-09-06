# P1 — Accounting + VAT

Status: P1A + P1B + P1C implemented

## Boundary

ERPNext remains the transaction, tax calculation and GL engine. `erpnext_vietnam` provides legal classification, effective-dated metadata, Company-specific statutory account mapping, validation and immutable evidence hashes. No handler posts GL entries or replaces ERPNext tax calculation.

## Accounting mapping

`VN COA Mapping` maps canonical semantic roles (for example `VAT_OUTPUT_PAYABLE`) to the actual ERPNext `Account` of one Company and accounting regime. Suggested TT99 account numbers are metadata only and are never referenced by transaction handlers. Overlapping mappings for the same Company/role/regime are rejected.

## VAT treatments

The legal layer keeps distinct treatments: `NON_TAXABLE`, `ZERO_RATE_0`, `REDUCED_5`, `TEMP_REDUCED_8`, `STANDARD_10`. A generic `STANDARD_10` classification may be explicitly marked eligible for a temporary reduction; the actual temporary rate/effective dates are resolved from released `VN Rate Rule` data, not hard-coded in invoice handlers.

## Native ERPNext integration

Items receive an optional `VN VAT Classification` link. Sales/Purchase Invoice Item rows snapshot the resolved legal treatment, rate and SHA-256 evidence. If the Company's mapped VAT control account is present in ERPNext's native `item_tax_rate`, P1 validates that native Item Tax Template rate against the resolved legal rate. Mixed-rate invoices remain native ERPNext invoices.

Purchase Invoice rows additionally carry input-VAT deduction status, deductible ratio and evidence reference. P1 validates ratio bounds and preserves evidence fields. P1C reads these fields for evidence coverage but does not calculate or submit a statutory declaration.

## Rollout safety

The app is inert for a Company until `VN Localization Settings` exists and VAT is configured. `VAT Validation Mode` supports Off, Advisory and Strict; missing classifications are only blocking in Strict mode. Selecting an invalid/expired/released classification or a contradictory native VAT rate is always rejected because it is explicit evidence, not a heuristic.

## Reference legal seed

P1A seeds versioned, globally inert reference records for the VAT legal chain (Law 48/2024/QH15 and effective amendments, Decree 181/2025/NĐ-CP and effective amendments, Circular 69/2025/TT-BTC), Resolution 204/2025/QH15 + Decree 174/2025/NĐ-CP for the temporary reduction, and Circular 99/2025/TT-BTC for accounting. The temporary 8% rule is effective 2025-07-01 through 2026-12-31. Generic VAT classification templates are never auto-assigned to Items.

P1B includes the complete TT99/2025 Appendix II reference catalog verified from the official Công Báo PDF: 184 statutory codes, including 71 level-1 accounts. `VN Statutory Account` is released read-only reference data carrying source-page and SHA-256 lineage. Company mapping remains explicit and reviewable. Domain presets may recommend mappings but never infer tax treatment automatically.

## P1C reconciliation

`VN VAT Reconciliation` is a read-only Script Report plus whitelisted read API. It resolves effective-dated Company mappings for VAT output and deductible input accounts, reads native ERPNext `GL Entry`, and reports output/input/net VAT accounting movement. It never posts or adjusts GL.

The report separately measures invoice-level VAT snapshot coverage, row-level legal-treatment coverage, Purchase Invoice input-VAT evidence coverage, and GL-voucher linkage to VAT snapshots. Journal/correction GL entries remain visible as accounting movement but are counted separately from invoice evidence. Mapping gaps and ambiguous input/output account mappings are warnings; ambiguous entries are excluded rather than guessed.

P1C is explicitly pre-declaration reconciliation. It creates no `VN Tax Declaration`, does not infer a filing return, and does not activate or call the Compliance Gateway. Formal declarations/submission remain a later compliance phase.
