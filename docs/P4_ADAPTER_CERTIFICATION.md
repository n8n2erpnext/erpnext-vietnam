# P4E — Production Adapter Certification Gate

Status: implemented; live rollback gate pending.

A registered adapter is not automatically eligible for production. `SANDBOX` adapters remain usable for conformance tests, but an enabled `PRODUCTION` endpoint requires a RELEASED `AdapterCertification` registered in code with the adapter. Database values cannot name a Python import path or self-certify an adapter.

Each certification pins a provider name, certification version, review date and official technical artifacts. At minimum it must include a `TECHNICAL_CONTRACT` or `API_SPEC` plus a `PAYLOAD_SCHEMA`, and every artifact carries a source reference, external version and SHA-256 digest. These are engineering provenance pins, not legal self-certification.

When a production endpoint is explicitly saved after review, `VN Integration Endpoint` stores the certification version and canonical certification hash. At runtime the gateway recomputes the in-code certification hash and refuses transport if the stored pin is missing or stale. An app upgrade that changes the certification therefore cannot silently keep transporting through an old operator approval.

No provider credentials, access tokens, private keys or passwords belong in certification metadata. Endpoint credential/signing fields remain references to external secret/signing systems. P4E adds no production adapter and performs no network call. A real adapter still requires provider-specific official technical material before its certification can be authored.
