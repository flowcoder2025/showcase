"""Progress event contract — fire-and-forget signature for scenario callbacks (T35/T38, R2-H3).

`progress_cb: Callable[[ProgressEvent], None]` — scenario가 진행 상황을 보고할
때 호출. CLI는 무시 가능, Streamlit은 진행바 갱신, future webapp은 SSE 등으로
재발신. 예외는 caller가 swallow (fire-and-forget) — scenario 본 흐름을 끊지
않는다.
"""

from __future__ import annotations

from typing import Any, TypedDict


class ProgressEvent(TypedDict):
    """Scenario 진행 단계 보고.

    Fields:
        kind: 이벤트 종류 — ``start`` / ``step`` / ``done`` / ``warn`` / ``error``.
        case_id: 발신 case 식별자 (예: ``case01``).
        message: human-readable 단계 설명 (한글).
        index: 현재 단계 진행 수 (multi-step에서만).
        total: 전체 단계 수 (multi-step에서만).
        extra: 자유 형식 추가 컨텍스트 (rate-limited backend 응답 등).
    """

    kind: str
    case_id: str
    message: str
    index: int | None
    total: int | None
    extra: dict[str, Any]
