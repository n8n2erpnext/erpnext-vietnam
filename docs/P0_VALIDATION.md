# P0 Foundation Validation

Validated on 2026-09-06 against Frappe/ERPNext v16 on the real `erp.thaiduy.digital` site.

## Distribution and install

Public source: `https://github.com/n8n2erpnext/erpnext-vietnam.git`. A clean `bench get-app ... --branch main` clone succeeded and produced the normal bench app directory `apps/erpnext_vietnam`. The app then built and installed successfully as `erpnext_vietnam 0.1.0-dev`.

The bench service account uses NVM, so non-login automation must expose the Node binary on PATH before `bench build` / `bench get-app`. On this validation host the path was `/home/ubuntu/.nvm/versions/node/v24.15.0/bin`. This is an operational environment detail, not an app dependency.

A site backup was created before first install. Running workers needed one normal `bench restart` after the first editable-package install so pre-existing Gunicorn processes could import the newly installed Python package. No Frappe/ERPNext/HRMS core patch was required.

## Foundation schema

The real-site migration synced the Vietnam Localization module successfully. Foundation objects are present for legal instruments, rule sets/rates, company localization settings, statutory COA mapping, integration endpoints, submissions and submission attempts. `VN Business Profile` was seeded with 15 neutral domain presets.

Safe post-migration state was verified: 15 business profiles; zero integration endpoints; zero submissions; zero company localization settings. Therefore installation itself does not activate compliance transport or mutate a Company configuration.

## Setup UX

Frappe v16 marks third-party applications as `has_setup_wizard = 0` in the Installed Applications registry. The app therefore does not patch that core behavior. Fresh-site setup can still participate through Frappe setup hooks, while existing sites receive the native Desk page `vn-setup-wizard` (`/app/vn-setup-wizard`). Both paths use the same backend snapshot builder.

The Desk page is restricted to System Manager, offers Preview before Apply, and explicitly states that tax/BHXH external submission remains disabled. The two setup JavaScript entry points passed `node --check`.

## Read-only preview validation

A real-site preview was executed against a controlled deployment test Company with profile `SOFTWARE_SAAS`, accounting regime `TT99_2025`, VAT method `DEDUCTION`, and payroll/social-insurance/e-invoice toggles disabled. The backend returned deterministic snapshot hash `4e7b710cb69c836fe45b168e22898c4fceab9b83aa6b7d790a7b90e3212d307d`.

The preview explicitly returned `enable_compliance_gateway: false`, no warnings, and the planned changes only. `VN Localization Settings` remained at zero rows after preview, proving the preview path is non-mutating. No setup profile was applied by the validation run.

## Automated checks

15 Python unit tests pass, covering domain profile stability, rule resolution/history, deterministic hashes, gateway idempotency, P0 schema, safe gateway defaults, optional HRMS dependency, safe install lifecycle and setup preview contract. Python AST, DocType JSON and JavaScript syntax checks also pass.

Final app commit deployed during this validation: `393ed6d`. Final public site HTTP check returned 200.

## P0 gate

P0 foundation is considered implementation-complete for the current scope. P1 may build accounting/VAT logic on top of these contracts without changing Frappe/ERPNext core, without making HRMS mandatory, and without enabling any external government/provider endpoint by default.
