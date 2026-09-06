# ERPNext Vietnam Localization

Universal Vietnam localization/compliance app for Frappe + ERPNext + HRMS.

Design rules: core apps remain unchanged; legal rules are effective-dated and auditable; external integrations use provider-neutral adapters; product-specific consumers are not dependencies of this app.

Current phase: P0 foundation. See `PLAN.md`, `ARCHITECTURE_V0.md`, and `research/VIETNAM_LOCALIZATION_DEEP_RESEARCH.md`.
## Installation model

The app is designed for the standard Frappe distribution flow: a public Git repository, `bench get-app`, then `bench --site <site> install-app erpnext_vietnam`. It targets Frappe/ERPNext/HRMS v16 first. The repository coordinate planned for publication is `n8n2erpnext/erpnext-vietnam`; until that repository exists, use this source tree only for development/testing.

After installation, ERPNext Vietnam exposes its own Setup Wizard. The wizard asks for Company, business domain, accounting regime, VAT method and optional payroll/social-insurance/e-invoice preparation. Domain selection is only a preset and never overrides effective-dated legal rules.

