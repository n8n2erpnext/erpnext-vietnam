from __future__ import annotations

import hashlib

STATUSES = (
    "DRAFT", "PREPARED", "QUEUED", "SUBMITTING", "ACCEPTED", "REJECTED",
    "UNKNOWN", "ADJUSTED", "REPLACED", "CANCELLED",
)

TRANSITIONS = {
    "DRAFT": {"PREPARED", "CANCELLED"},
    "PREPARED": {"QUEUED", "CANCELLED"},
    "QUEUED": {"SUBMITTING", "CANCELLED"},
    "SUBMITTING": {"ACCEPTED", "REJECTED", "UNKNOWN"},
    "UNKNOWN": {"ACCEPTED", "REJECTED"},
    "ACCEPTED": {"ADJUSTED", "REPLACED", "CANCELLED"},
    "REJECTED": {"PREPARED", "CANCELLED"},
    "ADJUSTED": set(),
    "REPLACED": set(),
    "CANCELLED": set(),
}


def transition_allowed(old: str, new: str) -> bool:
    return new == old or new in TRANSITIONS.get(old, set())


def operation_idempotency_key(company: str, sales_invoice: str, operation: str, revision: int = 1) -> str:
    raw = "|".join([company.strip(), sales_invoice.strip(), operation.strip().upper(), str(int(revision))])
    return "VN-EINV:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
