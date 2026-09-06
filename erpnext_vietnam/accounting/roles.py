from __future__ import annotations

# Canonical semantic roles. Suggested statutory codes are metadata only; business
# logic resolves a Company-specific VN COA Mapping and never hard-codes an account.
STATUTORY_ROLES = {
    "CASH_ON_HAND": "111",
    "DEMAND_DEPOSIT": "112",
    "ACCOUNTS_RECEIVABLE": "131",
    "VAT_INPUT_DEDUCTIBLE_GOODS_SERVICES": "1331",
    "VAT_INPUT_DEDUCTIBLE_FIXED_ASSETS": "1332",
    "INVENTORY": "156",
    "ACCOUNTS_PAYABLE": "331",
    "VAT_OUTPUT_PAYABLE": "33311",
    "REVENUE_GOODS_SERVICES": "511",
    "COST_OF_GOODS_SOLD": "632",
}

VAT_OUTPUT_ROLE = "VAT_OUTPUT_PAYABLE"
VAT_INPUT_ROLE = "VAT_INPUT_DEDUCTIBLE_GOODS_SERVICES"


def validate_statutory_role(role: str) -> str:
    role = (role or "").strip().upper()
    if role not in STATUTORY_ROLES:
        raise ValueError(f"unknown Vietnam statutory role: {role}")
    return role
