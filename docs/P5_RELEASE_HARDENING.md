# P5 — Release Hardening and Operator UX

Status: P5A deployed; P5B next.

## P5A — Vietnam Localization Health

`/desk/vn-localization-health` is a read-only operational health surface. It reports the selected Company setup snapshot, accounting regime/VAT method, optional HRMS presence, enabled compliance features, COA mapping count, e-invoice profile count, enabled integration endpoints, production endpoint certification-pin state and current statutory artifact counts.

The health API requires read permission on the Company and contains no insert/save/set-value/commit path. Its status is operational readiness only; it never claims legal, tax or filing certification. The Setup page links directly to Health, and Health links back to Setup.

### Live validation — 2026-09-06

For `LightBI Inc`, the applied setup is `SOFTWARE_SAAS / TT99_2025 / DIRECT`, PIT payroll ON, social insurance ON, e-invoice preparation ON, and Compliance Gateway OFF. Health returned `READY_WITH_WARNINGS`: HRMS is installed, while `VN COA Mapping` and `VN E-Invoice Profile` are still empty. Those are reported as explicit warnings rather than silently generating accounting mappings or provider configuration.

## P5B — next

Add a reproducible release doctor and install/upgrade smoke contract for public `bench get-app` consumers. It must verify supported Frappe/ERPNext major versions, optional HRMS behavior, required DocTypes/Pages, seed integrity and safe defaults without enabling external transport.
