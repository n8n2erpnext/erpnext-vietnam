from __future__ import annotations

import json
from pathlib import Path

CATALOG_PATH = Path(__file__).with_name("tt99_2025_chart.json")
TT99_CATALOG_VERSION = "TT99_2025_APPENDIX_II_V1"


def load_tt99_catalog() -> dict:
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if data.get("catalog_version") != TT99_CATALOG_VERSION:
        raise ValueError("Unexpected TT99 catalog version")
    return data


def validate_catalog(data: dict | None = None) -> None:
    data = data or load_tt99_catalog()
    rows = data["records"]
    codes = [row["account_code"] for row in rows]
    if len(codes) != len(set(codes)):
        raise ValueError("TT99 catalog contains duplicate account codes")
    by_code = {row["account_code"]: row for row in rows}
    for row in rows:
        parent = row.get("parent_code")
        if parent and parent not in by_code:
            raise ValueError(f"Missing TT99 parent {parent} for {row['account_code']}")
        if parent and not row["account_code"].startswith(parent):
            raise ValueError(f"Invalid TT99 hierarchy {parent} -> {row['account_code']}")
