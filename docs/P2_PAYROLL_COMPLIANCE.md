# P2 — Vietnam Payroll Compliance

Status: P2A/P2B implementation checkpoint; live parallel-payroll UAT remains required before a legal-compliance release label.

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

## Not implemented in this checkpoint

P2 does not yet insert HRMS deduction rows, create employer-contribution Journal Entries, or reconcile configured Salary Components against the independent statutory calculation. That is P2C. P3 owns 05/KK-TNCN, 05/QTT-TNCN and BHXH administrative exports.
