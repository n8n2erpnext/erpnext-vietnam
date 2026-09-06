# ERPNext Vietnam Localization

Universal Vietnam localization/compliance app for Frappe + ERPNext + HRMS.

Design rules: core apps remain unchanged; legal rules are effective-dated and auditable; external integrations use provider-neutral adapters; product-specific consumers are not dependencies of this app.

Current phase: P3 statutory declarations/adapters. See `PLAN.md`, `ARCHITECTURE_V0.md`, and `research/VIETNAM_LOCALIZATION_DEEP_RESEARCH.md`.

## Development topology

The canonical development workspace is the host-side Git repository at `/home/ubuntu/n8n2erpnext/.erpnext-vietnam-localization`. All design, code, tests, docs, commits and GitHub pushes originate there. The Frappe app checkout inside LXD at `/home/ubuntu/frappe/frappe-bench/apps/erpnext_vietnam` is a deployment/runtime copy only; it must be fast-forwarded from GitHub as user `ubuntu`, then migrated/tested on the site. Do not treat the LXD checkout as the development source of truth.

## Installation model

The app uses the standard Frappe distribution flow: public repository `n8n2erpnext/erpnext-vietnam`, `bench get-app https://github.com/n8n2erpnext/erpnext-vietnam`, then `bench --site <site> install-app erpnext_vietnam`. It targets Frappe/ERPNext v16 first, with HRMS-dependent features enabled only when HRMS is installed.

After installation, ERPNext Vietnam exposes its own Setup Wizard. The wizard asks for Company, business domain, accounting regime, VAT method and optional payroll/social-insurance/e-invoice preparation. Domain selection is only a preset and never overrides effective-dated legal rules.

