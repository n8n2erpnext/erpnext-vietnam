# P4 — E-Invoice and Compliance Gateway

Status: P4A provider-neutral e-invoice preparation deployed; P4B gateway orchestration live rollback gate passed.

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


## P4B gateway orchestration

Adapters are registered explicitly in code; the database stores only an adapter ID and cannot import an arbitrary Python path. Every enabled endpoint must match the registered adapter channel. Endpoint capabilities can further narrow operations supported by the adapter. The built-in `sandbox.einvoice.v1` adapter is for tests only and is rejected for every `PRODUCTION` endpoint.

Transport is double-gated: Company-scoped `enable_compliance_gateway` must be true and the selected `VN Integration Endpoint` must be enabled. A submission starts as Draft, passes adapter validation into Ready, then records an audit attempt before Submit. Completed attempts are immutable audit records and cannot be deleted.

An ambiguous timeout after Submit is persisted as `UNKNOWN`. The core refuses another Submit while Unknown and requires `RECONCILE`; reconciliation may resolve to Accepted or Rejected. The sandbox adapter deliberately simulates a provider that accepted a request before the timeout, allowing the UAT to prove that the provider Submit call remains exactly one while reconciliation recovers the accepted truth.

The P4B live gate is rollback-only: it temporarily enables the gateway inside a transaction, creates a sandbox endpoint/submission, simulates the ambiguous timeout, verifies blind retry is blocked, reconciles to Accepted, checks GL and Journal Entry counts, then rolls back every setup/endpoint/submission/attempt record. No production adapter and no external network call are present in this checkpoint.


## P4B live rollback result — 2026-09-06

On `erp.thaiduy.digital`, the sandbox UAT ran against a Company-scoped temporary configuration entirely inside a rollback transaction. GL Entry stayed 251, Journal Entry stayed 2, and the persistent counts for Localization Settings, Integration Endpoint, Submission and Submission Attempt all returned to their pre-UAT zero state.

The operation sequence was exactly `VALIDATE/SUCCESS → SUBMIT/UNKNOWN → RECONCILE/SUCCESS`; blind re-submit while Unknown was rejected and the sandbox provider submit counter remained exactly 1. Reconciliation recovered `ACCEPTED`. This closes the P4B engineering gate without enabling a real provider or making an external network call.


## P4C explicit e-invoice bridge

A Prepared `VN E-Invoice` can be manually queued into `VN Submission`. Queueing resolves exactly one enabled Company-scoped `VN E-Invoice Profile`, verifies the stored canonical payload/hash is still Ready, and calls only the gateway `VALIDATE` preparation path. It does not submit to a provider. Repeated Queue is idempotent and reuses the existing non-cancelled submission for the e-invoice.

The Desk form exposes status-driven manual actions only: Prepared → **Queue for Submission**, Queued → **Submit**, and Unknown/Submitting → **Reconcile**. The Sales Invoice `on_submit` hook is unchanged and remains local preparation-only. There is no automatic Queue or Submit path from ERPNext accounting documents.

Submission status is mirrored back onto `VN E-Invoice`; an ambiguous Submit sets both records to Unknown, and only Reconcile can resolve provider truth. Provider external references are recorded as request references without pretending they are final tax-authority invoice codes.
