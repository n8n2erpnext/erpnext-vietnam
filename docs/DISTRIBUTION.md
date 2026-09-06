# Distribution contract

Target public repository: `n8n2erpnext/erpnext-vietnam`.

User-facing install flow once published:

```bash
bench get-app https://github.com/n8n2erpnext/erpnext-vietnam
bench --site your-site install-app erpnext_vietnam
```

Initial compatibility target is Frappe/ERPNext/HRMS v16. `main` tracks the current supported v16 line during pre-1.0 development; if multiple Frappe major versions are supported later, maintain explicit compatibility branches/tags.

The app remains universal: no product-specific dependency or consumer-specific field/API is allowed in the runtime core. Product integrations live outside the localization app or in reference documentation.

## Runtime notes from real Frappe v16 validation

The public GitHub `bench get-app` flow has been verified on a real bench. If Bench is launched from automation/non-login shells and Node is installed through NVM, make sure the active Node bin directory is on `PATH` before asset build. This is host configuration, not an application requirement.

After installing a new Python app into a running production bench, restart the bench processes once so existing workers load the editable package. Normal later `bench migrate` / deploy operations follow the bench's standard lifecycle.

For an existing ERPNext site, open `/app/vn-setup-wizard` after install. Preview is non-mutating; Apply creates the Company-specific localization settings. External compliance endpoints remain disabled until separately configured.


## Supported compatibility

The current development line targets Frappe `16.x` and ERPNext `16.x`. HRMS is optional; when installed for payroll/social-insurance features, the supported major is HRMS `16.x`. The release doctor fails closed on unsupported Frappe/ERPNext majors and reports the installed versions before release or upgrade.

Before a production upgrade, run:

```bash
bench --site your-site execute erpnext_vietnam.diagnostics.release_doctor.run
```

A PASS confirms the engineering compatibility contract only; it is not legal/tax certification.
