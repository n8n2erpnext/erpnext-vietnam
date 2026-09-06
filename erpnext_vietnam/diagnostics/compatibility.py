from __future__ import annotations

import re

SUPPORTED_MAJORS = {
    "frappe": {16},
    "erpnext": {16},
    "hrms": {16},
}


def parse_major(version: str | None) -> int | None:
    if not version:
        return None
    match = re.match(r"^\s*(\d+)", str(version))
    return int(match.group(1)) if match else None


def is_supported(app: str, version: str | None) -> bool:
    major = parse_major(version)
    allowed = SUPPORTED_MAJORS.get(app)
    return bool(allowed and major in allowed)
