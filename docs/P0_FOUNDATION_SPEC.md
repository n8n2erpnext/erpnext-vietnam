# P0 Foundation Specification

## Runtime contracts

The P0 runtime is intentionally product-neutral and has no government endpoint enabled by default.

### Legal rule identity
A released rule is identified by `code + effective_from + priority`, and must carry legal references before production release. Historical documents store a rule snapshot hash. A new legal amendment creates a new released rule; it never mutates a historical released rule in place.

### Company boundary
All statutory calculations and submissions are company-scoped. Company configuration selects accounting regime, active released rule set, submission adapters and statutory account mappings. No Company name is hard-coded in Python.

### Submission boundary
Business logic creates a canonical payload. The Compliance Gateway creates a submission record, computes payload hash/idempotency, invokes an adapter, stores every attempt and reconciles ambiguous network outcomes before any retry.

### Security boundary
Endpoint credentials, signing secrets and certificates are references to a secret backend/provider configuration. Raw private keys are never ordinary DocType values and never fixtures.

## First DocTypes to implement

1. `VN Legal Instrument`
2. `VN Rule Set`
3. `VN Rate Rule`
4. `VN Localization Settings`
5. `VN COA Mapping`
6. `VN Integration Endpoint`
7. `VN Submission`
8. `VN Submission Attempt`

VAT/payroll/e-invoice domain DocTypes begin only after these foundation contracts pass site-level tests.

## Dependency policy

`erpnext` is the only hard application dependency. HRMS integration is optional so accounting-only ERPNext sites can install the Vietnam localization app. Payroll/PIT/BHXH features must feature-detect HRMS at runtime and remain disabled when HRMS is absent.

## P0 completion criteria

P0 is complete only when all eight foundation DocTypes migrate on a real Frappe v16 site, the setup wizard registers as an app-specific wizard, domain profile sync is idempotent, no external endpoint is enabled by default, and a clean `bench get-app` from the public GitHub repository succeeds.
