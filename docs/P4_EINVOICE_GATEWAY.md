# P4 — E-Invoice and Compliance Gateway

Status: P4A provider-neutral e-invoice preparation implemented; P4B transport orchestration pending.

## Legal/source boundary

The current 2026 legal baseline is Decree 254/2026/ND-CP and Circular 91/2026/TT-BTC, both effective 2026-07-01. The application records these as legal-source metadata, but does not infer a provider or tax-authority machine schema from the legal PDF alone. Provider/authority technical schemas are separate, versioned adapter artifacts.

## P4A canonical e-invoice

`VN E-Invoice` is a statutory companion to a submitted ERPNext Sales Invoice. It never posts GL. The canonical object is provider-neutral and records seller/buyer identity, source invoice reference, currency, line net values, P1 VAT classification/treatment/rate/snapshot evidence, VAT reporting category and reconciled totals.

The canonical model is fail-closed. It remains Draft when required identity or VAT evidence is absent, when line VAT does not reconcile to the native mapped `VAT_OUTPUT_PAYABLE` tax row, or when the Sales Invoice contains tax rows requiring accountant review. Only a canonical payload with `ready=true` may become Prepared.

## Feature and transport safety

The Sales Invoice `on_submit` hook first checks Company-scoped `VN Localization Settings.enable_einvoice`. If the Company is not configured or e-invoice preparation is disabled, the hook returns before building or creating any companion record. Even when enabled, the hook only prepares a local `VN E-Invoice`; it never calls an adapter, provider, tax authority, `VN Submission`, or Compliance Gateway.

`VN E-Invoice Profile` stores only provider-neutral endpoint/signing references. Raw private keys, API secrets and passwords are forbidden from ordinary DocType fields. A profile cannot be enabled unless its endpoint belongs to the same Company, uses the `E_INVOICE` channel, and is itself enabled.

## Lifecycle

Lifecycle states are `DRAFT → PREPARED → QUEUED → SUBMITTING → ACCEPTED/REJECTED/UNKNOWN`; `UNKNOWN` may only reconcile to `ACCEPTED` or `REJECTED` and cannot blindly resubmit. Accepted records may enter statutory `ADJUSTED`, `REPLACED`, or `CANCELLED` terminal states. Canonical source fields become immutable once transport starts.

Each issue operation receives a revision-scoped deterministic idempotency key. Final XML/rendering, provider IDs, authority code and signing-certificate metadata are archive fields; the signing key itself is never stored.

## P4B next

P4B will turn the existing `VN Integration Endpoint`, `VN Submission`, and `VN Submission Attempt` foundation into an explicit adapter registry/orchestrator. It must validate endpoint capabilities, create immutable attempts, treat network ambiguity as `UNKNOWN`, reconcile before retry, and prove zero duplicate submission in a sandbox-only rollback UAT before any real provider adapter is added.
