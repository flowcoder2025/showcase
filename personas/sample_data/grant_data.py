"""AX상사 정부지원사업 신청 시드 데이터 (case06).

Single application record consumed by ``cases.case06_hwpx_govt_form_filler``.
Values mirror the persona company defined in ``personas/company.md`` and the
김사장 character; biznum reuses the algorithm-valid public test biznum used
across case08 tests so the demo stays consistent with the rest of the suite.

Field order in ``GrantApplication`` matches the row order embedded in
``personas/sample_data/forms/grant_application_template.hwpx`` (left-column
labels at rows 0..7), so the scenario can map row index → field deterministically.
"""

from __future__ import annotations

from typing import Final, TypedDict


class GrantApplication(TypedDict):
    """One row of an AX상사 government grant application form."""

    company_name: str
    ceo_name: str
    biznum: str
    business_area: str
    grant_amount: int
    annual_revenue: int
    employee_count: int
    application_date: str  # ISO-8601 (YYYY-MM-DD)


AX_TRADING_GRANT: Final[GrantApplication] = {
    "company_name": "AX상사",
    "ceo_name": "김민준",  # 김사장 persona
    "biznum": "220-81-62517",  # algorithm-valid public test biznum (case08 fallback)
    "business_area": "제조·유통(IoT 기반 재고관리)",
    "grant_amount": 50_000_000,
    "annual_revenue": 1_200_000_000,
    "employee_count": 32,
    "application_date": "2026-05-15",
}
