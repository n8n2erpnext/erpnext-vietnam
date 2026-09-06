from __future__ import annotations

import hashlib


def make_idempotency_key(*parts: str) -> str:
    normalized = ":".join(p.strip() for p in parts)
    digest = hashlib.sha256(normalized.encode()).hexdigest()[:24]
    return f"VN:{digest}"
