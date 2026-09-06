# P1B — TT99/2025 Appendix II statutory account catalog

Status: implemented from the official Công Báo PDF.

Source: Circular 99/2025/TT-BTC, Appendix II, Section A — `Hệ thống tài khoản kế toán doanh nghiệp`. The source PDF is the official Government Gazette artifact, SHA-256 `2f8edab015d1291675d58e9b4452641350a66a5b5d23f47c85ca6dfd9953c99d`.

Catalog version: `TT99_2025_APPENDIX_II_V1`. Effective from: `2026-01-01`. Source PDF indexes 32–42, corresponding to printed Công Báo pages 34–44.

The catalog contains 184 unique account codes: 71 level-1 accounts and 113 subaccounts. Parent relationships are derived only from account-code hierarchy verified within the same Appendix II list. Extraction-only spacing artifacts in four Vietnamese words were normalized without changing meaning.

`VN Statutory Account` is app-owned read-only reference data. Released rows are immutable; a future legal amendment must publish a new catalog version instead of rewriting historical reference records.

`preview_company_mapping` compares the statutory catalog to one Company's existing ERPNext leaf Accounts. It prefers exact account-number matches, then exact normalized Vietnamese names. The result is explicitly read-only: it never creates, renames or changes ERPNext Accounts and never creates a `VN COA Mapping` automatically.

Canonical business logic continues to use semantic statutory roles. Suggested TT99 account numbers are lookup metadata only. The Company-specific `VN COA Mapping` remains the runtime bridge from a semantic role to an actual ERPNext Account.
