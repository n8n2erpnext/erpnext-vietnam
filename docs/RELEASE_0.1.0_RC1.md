# ERPNext Vietnam 0.1.0-rc1

Status: engineering release candidate.

Validated baseline: Frappe 16.17.0, ERPNext 16.16.0 and optional HRMS 16.5.4. A disposable MariaDB clean install passed ERPNext + ERPNext Vietnam installation, Release Doctor before/after migrate, 15/15 profile seeding, zero automatic Company configuration and zero external-integration records. The configured production regression also passed.

Install with the normal Frappe flow:

```bash
bench get-app https://github.com/n8n2erpnext/erpnext-vietnam --branch v0.1.0-rc1
bench --site your-site install-app erpnext_vietnam
```

After installation, System Managers can use ERPNext **Global Defaults / Cài đặt chung** -> **Vietnam Localization** instead of remembering a Desk URL. Setup remains explicit and Compliance Gateway remains disabled until separately configured.

Boundaries: native ERPNext remains the transaction/tax/GL engine; HRMS remains the payroll engine when installed; this app supplies Vietnam statutory interpretation, evidence, reconciliation and controlled transport contracts. No real provider adapter is production-certified in this RC unless its official technical contract/schema is separately pinned and reviewed. Accountant/legal acceptance remains external to software tests.
