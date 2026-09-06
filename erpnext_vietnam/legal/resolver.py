from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import date
from typing import Iterable

from .models import EffectiveRule


class RuleConflictError(ValueError):
    pass


def select_rule(rules: Iterable[EffectiveRule], code: str, when: date) -> EffectiveRule:
    candidates = [r for r in rules if r.code == code and r.applies_on(when)]
    if not candidates:
        raise LookupError(f"no released rule for {code} on {when.isoformat()}")
    candidates.sort(key=lambda r: (r.priority, r.effective_from), reverse=True)
    winner = candidates[0]
    tied = [r for r in candidates if (r.priority, r.effective_from) == (winner.priority, winner.effective_from)]
    if len(tied) > 1:
        raise RuleConflictError(f"ambiguous released rules for {code} on {when.isoformat()}")
    return winner


def snapshot_hash(rule: EffectiveRule) -> str:
    payload = asdict(rule)
    payload["effective_from"] = rule.effective_from.isoformat()
    payload["effective_to"] = rule.effective_to.isoformat() if rule.effective_to else None
    payload["value"] = str(rule.value)
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()
