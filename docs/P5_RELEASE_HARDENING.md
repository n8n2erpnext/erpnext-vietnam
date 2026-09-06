# P5 — Release Hardening and Operator UX

Status: P5A deployed; P5B implemented and live doctor PASS; P5C next.

## P5A — Vietnam Localization Health

`/desk/vn-localization-health` is a read-only operational health surface. It reports the selected Company setup snapshot, accounting regime/VAT method, optional HRMS presence, enabled compliance features, COA mapping count, e-invoice profile count, enabled integration endpoints, production endpoint certification-pin state and current statutory artifact counts.

The health API requires read permission on the Company and contains no insert/save/set-value/commit path. Its status is operational readiness only; it never claims legal, tax or filing certification. The Setup page links directly to Health, and Health links back to Setup.

### Live validation — 2026-09-06

For `LightBI Inc`, the applied setup is `SOFTWARE_SAAS / TT99_2025 / DIRECT`, PIT payroll ON, social insurance ON, e-invoice preparation ON, and Compliance Gateway OFF. Health returned `READY_WITH_WARNINGS`: HRMS is installed, while `VN COA Mapping` and `VN E-Invoice Profile` are still empty. Those are reported as explicit warnings rather than silently generating accounting mappings or provider configuration.

## P5B — Release doctor and compatibility contract

`erpnext_vietnam.diagnostics.release_doctor.run()` is read-only and can be executed through Bench before or after an upgrade. It verifies supported major versions, required app schema, setup pages, seed completeness, setup snapshot integrity, production-endpoint safety and certification pins.

Live result on `erp.thaiduy.digital`:

- Frappe `16.17.0`: PASS
- ERPNext `16.16.0`: PASS
- optional HRMS `16.5.4`: PASS
- critical VN DocTypes/Pages: PASS
- business profiles: `15/15`
- applied setup snapshot hashes: PASS
- sandbox adapter in production: none
- missing production certification pins: none
- overall: `PASS`, 0 failures, 0 warnings

Run it with:

```bash
bench --site your-site execute erpnext_vietnam.diagnostics.release_doctor.run
```

P5C will replay a clean install plus an upgrade/configured-company regression before any release-candidate tag is created.
