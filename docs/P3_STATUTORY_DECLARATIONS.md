# P3 — Statutory declarations and social-insurance exports

Status: P3A/P3B canonical preparation layer implemented; exact government-format adapters and accountant-reviewed export UAT remain pending.

## Boundary

P3 does not change ERPNext accounting, HRMS payroll, VAT calculation or P2 payroll evidence. It reads submitted accounting/payroll evidence and creates separate canonical statutory objects. No P3 preview or builder calls an external government/provider endpoint, posts GL, creates Journal Entries, or creates `VN Submission` records.

The pipeline is deliberately split:

`immutable accounting/payroll evidence -> calculation snapshot -> canonical statutory model -> format adapter -> future gateway submission`

Government XML/XLS/PDF layout changes therefore cannot silently change VAT/PIT/payroll calculation logic.

## Tax declaration model

`VN Tax Declaration` owns prepared/reviewed/released snapshots for `01/GTGT`, `05/KK-TNCN` and `05/QTT-TNCN`. Each record stores a canonical calculation snapshot JSON + SHA-256, canonical declaration JSON + SHA-256, source count, warnings, legal instrument, period and schema version.

The status flow is `Draft -> Prepared -> Reviewed -> Released`, with `Voided` as an explicit terminal branch. Released statutory content is immutable. Prepared/Reviewed/Released records cannot be deleted; they must be voided where appropriate.

`01/GTGT` currently derives its canonical evidence from P1 VAT reconciliation plus submitted Sales/Purchase Invoice snapshot references. `05/KK-TNCN` and `05/QTT-TNCN` aggregate submitted Salary Slip evidence (`VN Payroll Calculation Line`) and keep per-employee/source-slip traceability.

## BHXH export model

`VN Social Insurance Export` prepares canonical `TK1-TS`, `TK3-TS` and `D02-LT` payloads independently from payroll calculation. The current official BHXH administrative-procedure page is pinned as the source baseline, together with SHA-256 hashes of the official PDF forms downloaded on 2026-09-06.

The canonical builders intentionally do not claim to be submission-ready. `adapter_ready` remains false until the exact official field/layout adapter has been transcribed, versioned, tested against the pinned forms, and reviewed.

## Official source baseline

Tax declaration source baseline: Circular `89/2026/TT-BTC`, issued 2026-06-30 and effective 2026-07-01. The official signed PDF is pinned in `p3_seed.py` with SHA-256 `952c45ffc0f10bfc176bd9ae6b3d204fd3a034294ee270278957b9c11e1471dc`.

BHXH official procedure page identifies `TK1-TS`, `TK3-TS` and `D02-LT`. Pinned official form hashes:

- `TK1-TS`: `629efd6340e2baef003dd4a7069f287140abda468a8d6a8aa9f69dd56e6ef225`
- `TK3-TS`: `f045e830adb50555529e0a17eb4ddcf39c1e6da54e1098abd4ba25c3309220bd`
- `D02-LT`: `29ce038a9de1a04cfd7b75f26bd5366bb04282f3bb16b70dcd781f0c39850a0d`

## Remaining P3 gate

P3C must implement exact form-indicator/column adapters separately from the canonical builders, then run controlled reconciliation/UAT against accountant-reviewed vectors. No direct government submission is part of the P3 gate; transport remains a later gateway phase.
