from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FormSpec:
    code: str
    title: str
    domain: str
    period_types: tuple[str, ...]
    schema_version: str


TAX_FORMS = {
    "01_GTGT": FormSpec("01/GTGT", "VAT declaration", "TAX", ("Month", "Quarter"), "canonical-v1"),
    "05_KK_TNCN": FormSpec("05/KK-TNCN", "Periodic PIT withholding declaration", "TAX", ("Month", "Quarter"), "canonical-v1"),
    "05_QTT_TNCN": FormSpec("05/QTT-TNCN", "Annual PIT finalization declaration", "TAX", ("Year",), "canonical-v1"),
}

BHXH_FORMS = {
    "TK1_TS": FormSpec("TK1-TS", "Participant information declaration", "SOCIAL_INSURANCE", ("As Of",), "canonical-v1"),
    "TK3_TS": FormSpec("TK3-TS", "Employer information declaration", "SOCIAL_INSURANCE", ("As Of",), "canonical-v1"),
    "D02_LT": FormSpec("D02-LT", "Labour use and participation list", "SOCIAL_INSURANCE", ("Month", "Custom"), "canonical-v1"),
}
