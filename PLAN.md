# ERPNext Vietnam Localization — Execution Plan

Status: active implementation

Source of truth: host workspace `/home/ubuntu/n8n2erpnext/.erpnext-vietnam-localization`. The LXD bench checkout is deployment/runtime only and must never become the development source of truth.

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
- [P3C implemented/deployed] Versioned TT89 tax indicator contracts, QĐ 505/1040 BHXH field/column contracts, additive VAT reporting taxonomy, adapter snapshot/hash persistence, historical guards and fail-closed `Needs Review` behavior; 78/78 tests PASS and production migrate verified.
- [P3D implemented/deployed] Deterministic XML/XLSX human-review packages for all six P3 form adapters, permission/Ready/hash gated and explicitly marked non-direct-upload; rollback-only Frappe UAT passed with zero GL/Journal Entry/VN Submission drift.
- [P3 engineering gate CLOSED 2026-09-06] Canonical preparation, statutory field/column contracts, immutable adapter snapshots, fail-closed review exports and live rollback UAT are complete. Accountant/legal validation remains an external acceptance activity, not something code may self-certify.

## P4 — E-invoice + external compliance adapters
- [P4A implemented] Provider-neutral `VN E-Invoice Profile` + `VN E-Invoice` companion lifecycle and canonical Sales Invoice payload under `VN-EINVOICE-CANONICAL-2026-01`.
- [P4A implemented] Submitted Sales Invoice hook is preparation-only and feature-gated by `VN Localization Settings.enable_einvoice`; it performs zero external transport and has no effect for unconfigured Companies.
- [P4A implemented] Canonical payload requires explicit seller/buyer identity, immutable P1 VAT snapshots and reconciliation to the mapped native VAT output account before becoming `PREPARED`.
- [P4B implemented] Explicit adapter registry/capability checks, Company+endpoint gateway gates, immutable audit attempts, timeout→UNKNOWN→reconcile semantics and sandbox-only rollback UAT harness.
- [P4B gate CLOSED 2026-09-06] Live rollback UAT proved synthetic timeout→UNKNOWN, blind retry blocked, RECONCILE→ACCEPTED, exactly one provider submit call, immutable 3-attempt audit trail, zero GL/Journal Entry change and zero persistent gateway/submission records after rollback.
- [P4C implemented] Bridge `VN E-Invoice` to `VN Submission` with explicit manual Queue/Submit/Reconcile actions and status-driven Desk buttons; Sales Invoice hooks remain preparation-only and never auto-transport.
- [P4C gate CLOSED 2026-09-06] Live rollback UAT on an existing submitted Sales Invoice proved Queue→READY, synthetic timeout→UNKNOWN, blind retry blocked, Reconcile→ACCEPTED, exactly one provider submit call, zero GL/Journal Entry change and zero persistent e-invoice/gateway records after rollback.
- [P4D gate CLOSED 2026-09-06] Accepted-provider evidence is normalized and immutable; private artifacts are SHA-256 verified; canonical/submission/evidence hashes are chained into the e-invoice archive. Live rollback UAT passed with one provider submit, immutable archive/evidence, zero GL/Journal drift, zero persistent VN records, and dedicated post-process artifact cleanup verified clean.
- [P4E gate CLOSED 2026-09-06] Production-adapter admission requires an in-code RELEASED certification with hash-pinned technical contract/API spec plus payload schema; production endpoints pin the certification version/hash and runtime rejects stale pins. Live rollback UAT proved uncertified production endpoints are blocked, a correctly pinned certified endpoint is admitted without transport, GL/Journal Entry are unchanged, and the endpoint rolls back cleanly.
- Tax/BHXH authority-specific direct-upload serializers only after an official machine schema/version is pinned; no schema is inferred from PDFs or UI screenshots.
- No provider credentials or private keys in ordinary DocTypes.

## P5 — Release hardening + operator UX
- [P5A implemented/deployed] Read-only Vietnam Localization Health reports Company setup, accounting/VAT mapping readiness, payroll/e-invoice readiness, gateway state and production-endpoint certification pins without changing data. Live validation on `LightBI Inc` returned `READY_WITH_WARNINGS`, correctly identifying empty COA mappings and missing e-invoice profile while keeping Compliance Gateway disabled.
- [P5B next] Add reproducible install/upgrade smoke checks for public `bench get-app` consumers and document supported Frappe/ERPNext/optional-HRMS compatibility.
- [P5C next] Freeze a release candidate only after clean install + upgrade + configured-company regression UAT; real provider adapters remain separately certified artifacts.

## Release gates
- Frappe/ERPNext/HRMS core unchanged.
- Every legal calculation references an effective-dated rule and legal instrument.
- Submitted historical results reproducible after upgrade.
- No direct external call during migrations.
- Source transaction == statutory evidence == declaration == GL control-account reconciliation.
