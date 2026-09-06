# P2 — Vietnam Payroll Compliance

Status: P2A/P2B/P2C implementation checkpoint; live parallel-payroll UAT remains required before the P2 release gate.

## Boundary

HRMS remains the payroll engine and ERPNext remains the accounting/GL engine. `erpnext_vietnam` does not change Salary Slip earnings, deductions, net pay or GL entries. The Vietnam layer classifies Salary Components, resolves effective-dated legal rules, calculates an independent statutory evidence view and snapshots it on Salary Slip submit.

HRMS is still optional in `required_apps`. P2 Custom Fields are created only when HRMS DocTypes exist.

## P2 reference model

- `VN Employee Tax Profile`: effective-dated residency/withholding mode and tax identity.
- `VN Dependent`: effective-dated dependent deduction evidence.
- `VN Social Insurance Profile`: participation flags, wage region and ordinary/special/exempt category.
- `VN Wage Region`: versioned regional minimum wage reference.
- `VN PIT Bracket`: immutable released progressive bracket reference.
- `VN Payroll Calculation Line`: immutable Salary Slip evidence line containing base, rate, floor, ceiling, amount, rule reference and snapshot hash.

## 2026 PIT baseline

The released reference set uses the five monthly resident brackets 5/10/20/30/35 percent at 10m/30m/60m/100m VND boundaries. Monthly family deductions are 15.5m VND for the taxpayer and 6.2m VND per eligible dependent. Nonresident salary mode uses a separately versioned 20% rule. Salary Component legal classification must be explicitly marked Reviewed before P2 can validate an enabled Company.

P2A intentionally supports Monthly VND Salary Slips only. Other frequencies or currencies are blocked rather than silently prorated or converted.

## Compulsory insurance baseline

Ordinary employee/employer rates are stored as effective-dated `VN Rate Rule` records, not Python constants: BHXH 8% employee / 17% employer, BHYT 1.5% / 3%, BHTN 1% / 1%, and ordinary BHTNLĐ-BNN 0.5% employer. Special/reduced categories are not inferred and require a later explicit rule profile.

The BHXH/BHYT reference floor/ceiling is effective-dated: 2.34m VND through 2026-06-30 and 2.53m VND from 2026-07-01, with the ordinary maximum at 20 times the active reference level. BHTN uses the selected wage-region minimum and a 20-times regional minimum ceiling. The 2026 released wage-region reference is Region I 5.31m, II 4.73m, III 4.14m and IV 3.70m VND/month.

## Salary Component metadata

P2 adds an explicit VN review gate plus PIT taxable/exemption/ratio metadata and separate BHXH/BHYT/BHTN base-inclusion flags. Default state is `Unreviewed`; enabling payroll compliance never guesses from the English/Vietnamese component name.

## Salary Slip evidence

On validate, when Company payroll compliance is enabled, P2 resolves the active employee tax/social profiles and active legal rules for the Salary Slip end date. Missing profiles, unreviewed Salary Components, unsupported special categories, missing wage region, unsupported frequency/currency or incomplete released rules are blockers.

On submit, P2 creates immutable `VN Payroll Calculation Line` records. Their canonical SHA-256 excludes the generated Salary Slip name so draft naming does not alter the evidence hash. Updating laws later creates new effective-dated rule versions and does not rewrite historical submitted Salary Slip evidence.

## P2C reconciliation and accrual preview

`VN Contribution Component` maps each employee-side statutory line (`PIT_WITHHOLDING`, `BHXH_EE`, `BHYT_EE`, `BHTN_EE`) to one reviewed HRMS Salary Component for one Company and effective period. Released overlapping mappings are rejected, and one Salary Component cannot silently represent multiple employee statutory lines during the same effective period.

`VN Payroll Reconciliation` compares immutable P2 evidence against the actual submitted Salary Slip deductions. It reports `MATCH`, `VARIANCE`, `UNMAPPED`, `NO_EVIDENCE` or evidence conflict rather than correcting payroll automatically. Employer-side lines are shown as expected-only because they do not reduce employee net pay.

The employer accrual API resolves semantic payable roles (`3335`, `3383`, `3384`, `3386` are catalog metadata behind Company-specific `VN COA Mapping`) and returns a read-only credit-side preview. It deliberately does not select expense allocation, create a Journal Entry or submit accounting. Expense allocation across production/sales/admin functions remains an explicit accounting decision.

## P2 release gate still pending

The site must run at least one controlled parallel payroll with reviewed Salary Components, employee tax/social profiles, wage region, contribution mappings and Company localization enabled. The independent P2 result must reconcile to HRMS deductions and the accountant-reviewed employer accrual before P2 is labeled production compliance-ready. P3 owns 05/KK-TNCN, 05/QTT-TNCN and BHXH administrative exports.
