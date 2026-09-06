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
- [P1A implemented] VN statutory-role mapping with overlap prevention and Company/account validation.
- [P1A implemented] VAT legal classification (`NON_TAXABLE`, `ZERO_RATE_0`, `REDUCED_5`, `TEMP_REDUCED_8`, `STANDARD_10`) with effective-dated temporary-reduction rule resolution.
- [P1A implemented] Additive Item/Sales Invoice/Purchase Invoice metadata + native Item Tax Template consistency validation + input-VAT evidence fields.
- [P1B implemented] Complete TT99/2025 Appendix II catalog from the official Công Báo PDF (184 codes; 71 level-1) as immutable versioned reference data + read-only Company mapping preview.
- [P1C implemented] Read-only pre-declaration VAT reconciliation from native GL + VAT snapshot/evidence coverage; no statutory filing or submission.

## P2 — Payroll compliance
- [P2A implemented] PIT employee profiles/dependents, five-bracket 2026 resident engine, nonresident salary rate, effective-dated family deductions.
- [P2A implemented] BHXH/BHYT/BHTN/BHTNLĐ-BNN ordinary contribution engine with 2026 reference-level transition and wage-region ceilings.
- [P2B implemented] Optional-HRMS Salary Component legal metadata + Salary Slip validation and immutable calculation-line snapshots; HRMS remains optional.
- [P2C implemented] Effective-dated contribution-to-HRMS-component mapping, Salary Slip deduction reconciliation report, payroll payable semantic roles and read-only employer accrual preview.
- [P2 gate CLOSED 2026-09-06] Controlled rollback-only live HRMS parallel-payroll UAT passed with reviewed components/profiles/mappings, immutable evidence, exact deduction reconciliation and zero Journal Entry/GL/VN Submission side effects.

## P3 — Statutory declarations
- [P3A implemented] `VN Tax Declaration` canonical preparation model for 01/GTGT, 05/KK-TNCN and 05/QTT-TNCN with source snapshots, deterministic hashes and release immutability.
- [P3B implemented] `VN Social Insurance Export` canonical TK1-TS, TK3-TS and D02-LT builders pinned to current official BHXH source PDFs.
- [P3B implemented] Read-only preview APIs are separate from explicit Prepared-record creation; no GL/Journal Entry/VN Submission/external transport side effects.
- [P3C pending] Exact government form indicator/column/XML/XLS adapters, accountant-reviewed vectors and export UAT. Format adapters remain separate from calculation logic.

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
