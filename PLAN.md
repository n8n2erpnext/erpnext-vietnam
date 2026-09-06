# ERPNext Vietnam Localization — Execution Plan

Status: active implementation

## P0 — Foundation
1. Universal Frappe app scaffold (`erpnext_vietnam`), no product-specific dependency.
2. Pure rule-selection core: effective dates, statuses, deterministic precedence, immutable snapshot hashing.
3. Legal registry model specification and fixtures format.
4. Generic Compliance Gateway contracts: endpoint, submission, attempts, idempotency and reconciliation.
5. Company/account statutory-role mapping contract.
6. App-specific Setup Wizard with versioned business-domain profiles, accounting/VAT choices, dry-run/preview contract and immutable setup snapshot.
7. Tests for historical reproducibility, rule overlap rejection, domain-profile stability and idempotency.

## P1 — Accounting + VAT
- TT99/2025 chart-of-accounts dataset imported as versioned legal data after direct Appendix II verification.
- VN statutory role mapping to ERPNext Account.
- VAT treatment classification (`NON_TAXABLE`, `ZERO_RATE_0`, `REDUCED_5`, `TEMP_REDUCED_8`, `STANDARD_10`).
- Sales/Purchase Invoice validation, input-VAT evidence and declaration reconciliation.

## P2 — Payroll compliance
- PIT profile/dependents and effective-dated PIT calculation.
- BHXH/BHYT/BHTN/BHTNLĐ-BNN contribution engine and ceilings.
- Immutable Salary Slip evidence and employer contribution accrual reconciliation.

## P3 — Statutory declarations
- 01/GTGT, 05/KK-TNCN, 05/QTT-TNCN canonical declaration models.
- TK1-TS, TK3-TS, D02-LT export models.
- Format adapters remain separate from calculation logic.

## P4 — E-invoice + external compliance adapters
- Provider-neutral VN E-Invoice lifecycle and canonical payload.
- Adapter interface for provider/tax-authority integrations.
- No provider credentials or private keys in ordinary DocTypes.

## Release gates
- Frappe/ERPNext/HRMS core unchanged.
- Every legal calculation references an effective-dated rule and legal instrument.
- Submitted historical results reproducible after upgrade.
- No direct external call during migrations.
- Source transaction == statutory evidence == declaration == GL control-account reconciliation.
