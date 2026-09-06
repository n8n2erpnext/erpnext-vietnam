# P1C — VAT Reconciliation

Status: implemented as a read-only pre-declaration control.

## Purpose

P1C answers one accounting-control question: do the VAT movements in ERPNext's native GL have enough Vietnam-localization evidence to be reviewed for a later statutory declaration? It does not calculate a tax return and it does not submit anything externally.

## Accounting source of truth

Amounts come only from submitted, non-cancelled `GL Entry` rows on Company-specific `VN COA Mapping` accounts. Output VAT uses credit minus debit. Deductible input VAT uses debit minus credit. The net shown is accounting movement only.

Mappings are resolved by posting date across the requested period. Both deductible goods/services and fixed-asset input VAT roles are supported. A gap in required mappings generates a warning. If the same account is simultaneously active as input and output VAT, matching entries are excluded and flagged rather than guessed.

## Evidence coverage

P1C counts submitted Sales/Purchase Invoices with document VAT snapshot hashes, classified item rows with legal-treatment hashes, Purchase Invoice input-VAT deduction/evidence fields, and VAT-control GL vouchers linked to invoice snapshots. Non-invoice GL movements such as Journal Entry corrections remain in the accounting movement and are counted separately.

P1C intentionally does not recompute invoice VAT from row net amounts. Native ERPNext tax calculation and posted GL remain authoritative; the localization layer only reconciles evidence around those postings.

## Interfaces

Standard report: `VN VAT Reconciliation` (Accounts User, Accounts Manager, System Manager).

Read API: `erpnext_vietnam.vat.reconciliation.get_vat_reconciliation(company, from_date, to_date)`. The API requires permission to read `GL Entry` and returns JSON-safe amounts, effective mapping lineage, coverage counters and warnings.

## Boundary

No GL posting, tax adjustment, declaration creation, gateway activation, credential use, provider adapter, or government submission exists in P1C. Formal declaration generation and submission remain outside P1.
