# Distribution contract

Target public repository: `n8n2erpnext/erpnext-vietnam`.

User-facing install flow once published:

```bash
bench get-app https://github.com/n8n2erpnext/erpnext-vietnam
bench --site your-site install-app erpnext_vietnam
```

Initial compatibility target is Frappe/ERPNext/HRMS v16. `main` tracks the current supported v16 line during pre-1.0 development; if multiple Frappe major versions are supported later, maintain explicit compatibility branches/tags.

The app remains universal: no product-specific dependency or LightBI-specific field/API is allowed in the runtime core. Product integrations live outside the localization app or in reference documentation.
