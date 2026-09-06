# ERPNext Vietnam Localization — Architecture V0

Status: research/design only. No production code yet.

## Goal

Build one independent Frappe app for Vietnam that layers on ERPNext + HRMS without modifying Frappe/ERPNext/HRMS core. Vietnamese legal logic is effective-dated, auditable, reproducible and replaceable as law changes.

## Dependency boundary

```text
Frappe Framework        unchanged
ERPNext / HRMS          unchanged
        │
        ▼
erpnext_vietnam
  ├─ legal registry
  ├─ accounting localization
  ├─ VAT / PIT
  ├─ payroll social insurance
  ├─ statutory declarations
  ├─ e-invoice adapters
  └─ setup / migration / audit
```

The app should prefer normal DocTypes, Custom Fields, fixtures, hooks and reports. Avoid `override_doctype_class` unless an upstream limitation makes extension impossible.
## Core data model

Recommended DocTypes:

- `VN Legal Instrument`: legal source, issuer, official URL, publication/effective/expiry dates, source hash.
- `VN Rule Set`: immutable released rule bundle with effective dates and snapshot hash.
- `VN Rate Rule`: effective-dated rate/formula rows linked to one or more legal instruments.
- `VN Localization Settings`: per-company accounting regime, rule-set defaults and feature flags.
- `VN COA Mapping`: statutory role -> actual ERPNext Account mapping.
- `VN VAT Classification`: taxable treatment, statutory rate, temporary reduction eligibility/exclusion and effective dates.
- `VN Employee Tax Profile`: tax ID, residency and withholding profile.
- `VN Dependent`: PIT dependent eligibility and validity period.
- `VN Social Insurance Profile`: BHXH/BHYT/BHTN participation, wage region and special category.
- `VN Payroll Calculation Line`: immutable calculation evidence per Salary Slip.
- `VN Tax Declaration`: 01/GTGT, 05/KK-TNCN, 05/QTT-TNCN and future declarations.
- `VN E-Invoice Profile` + `VN E-Invoice`: provider-neutral statutory invoice lifecycle and archive.

Use companion DocTypes for legal/audit-heavy objects. Use Custom Fields only where the value genuinely belongs on an ERPNext master or transaction.
## ERPNext integration map

`Company`: add Vietnam tax identity, accounting regime and localization settings link.

`Account`: keep ERPNext account tree; attach statutory code/role through mapping rather than hard-coded account numbers in Python.

`Item`: attach `VN VAT Classification`; use ERPNext Item Tax Template for actual rate application while the VN layer owns legal classification/effective dates.

`Sales Invoice`: validate VAT treatment, snapshot rule-set/hash, create or queue `VN E-Invoice` after submit. E-invoice issuance itself must not duplicate GL posting.

`Purchase Invoice`: capture deductible-input-VAT evidence/status/ratio and rule snapshot.

`Employee` / `Salary Component`: add only minimal VN attributes required for PIT and contribution-base classification.

`Salary Slip`: calculate against a released rule set, persist evidence lines, never silently recalculate old submitted slips after a law update.

`Payroll Entry`: create or reconcile employer-side statutory contribution accrual through ordinary ERPNext accounting primitives.
## Rule engine principles

1. No scattered legal constants in event handlers.
2. Every rate/formula/classification carries `effective_from`, optional `effective_to`, legal references and status.
3. Released rule sets are immutable; amendments create a new version.
4. Submitted documents store `vn_rule_set` and `vn_rule_snapshot_hash`.
5. Date selection is based on the legally relevant transaction/payroll date, not current server date.
6. New rules can run in shadow mode before activation.
7. Migrations never rewrite submitted historical accounting/payroll results.

## VAT architecture

Do not model VAT as only `0/5/8/10`. Distinguish at least `NON_TAXABLE`, `ZERO_RATE_0`, `REDUCED_5`, `TEMP_REDUCED_8`, `STANDARD_10`. The VN classifier determines legal treatment; ERPNext Tax Rule / Sales-Purchase Taxes and Charges Template / Item Tax Template perform the normal transaction calculation and GL integration.

Mixed-rate invoices therefore remain native ERPNext transactions while VN metadata drives classification, reporting and legal evidence.
## Payroll / PIT / social insurance

Do not encode one monolithic deduction formula. Each Salary Component needs VN flags for PIT taxability and BHXH/BHYT/BHTN base inclusion. The calculation engine resolves effective rates, ceilings, wage-region references and deductions, then emits immutable `VN Payroll Calculation Line` evidence tied to the Salary Slip.

The employer-side contribution should remain separately auditable from employee deductions. Payroll reports must reconcile calculation evidence -> Salary Slip -> Journal Entry / Payroll Entry liabilities.

## E-invoice boundary

`VN E-Invoice` is a statutory companion document linked to Sales Invoice. A canonical Vietnam invoice model feeds provider adapters such as VNPT/Viettel/MISA/FPT/BKAV only after provider-specific API review. Store idempotency key, request/response IDs, schema version, final XML, SHA-256, tax-authority/provider status and adjustment/replacement/cancellation chain. Never store raw private signing keys in ordinary DocType fields.

## Install / upgrade strategy

Ship Custom Fields and small configuration objects through fixtures where stable. Ship legal datasets/rules as versioned application data or patches with explicit release IDs. Setup wizard creates VN defaults only after company/accounting-regime confirmation. Upgrades add new rules; they never overwrite old released rule rows.
## Integration Gateway and first-party consumers

The localization app must expose a provider-neutral integration boundary from day one, even if direct submission to Vietnamese government systems is deferred. The goal is to avoid coupling tax, social-insurance, e-invoice, or product-specific integrations directly into accounting/payroll code.

### VN Compliance Gateway

Create a dedicated `integration` package and companion DocTypes such as `VN Integration Endpoint`, `VN Submission`, and `VN Submission Attempt`. The gateway owns transport, authentication metadata, signing handoff, retries, idempotency, provider response storage, reconciliation, and status polling. Business rule engines only produce canonical payloads.

```text
ERPNext / HRMS transaction
        -> VN canonical compliance object
        -> VN Compliance Gateway
             -> Tax adapter
             -> BHXH adapter
             -> E-invoice adapter
             -> future government/provider adapter
```

No tax/BHXH endpoint, certificate, vendor field, or API credential may be hard-coded in core rule modules. Direct integrations remain adapter packages activated only when an official or licensed-provider interface is available and legally/technically validated.

### Outbound government-facing interfaces

Reserve canonical operations such as `prepare`, `validate`, `submit`, `get_status`, `download_receipt`, `replace`, `adjust`, `cancel`, and `reconcile`. Each submission stores immutable source references, rule-set version, schema version, payload hash, idempotency key, provider request/response identifiers, timestamps, and final acknowledgement artifact. A timeout must trigger reconciliation before retry to prevent duplicate statutory submissions.

### Inbound business/application integration

The same app should expose a stable first-party API/event boundary for trusted systems that create business events in ERPNext. External systems must not write statutory tables directly. They submit commercial events to ERPNext; ERPNext remains the accounting source of truth; the Vietnam localization layer derives statutory classification, payroll/tax evidence, declarations, and submissions from those posted records.

## Universal consumer boundary

`erpnext_vietnam` is product-neutral. It must not contain product-specific DocTypes, fields, routes, constants, company names, customer names, or business rules. External systems integrate only through generic inbound commercial-event APIs and governed read APIs. Product-specific examples belong outside the core architecture and never become runtime dependencies.

### System-of-record boundary

- External operational systems own their own order/license/domain workflows.
- ERPNext owns posted commercial and accounting truth.
- `erpnext_vietnam` owns Vietnam statutory interpretation, evidence, declarations and compliance submissions.
- Analytics/BI consumers are read-only consumers of governed views and do not mutate released legal rules or submitted statutory records.
