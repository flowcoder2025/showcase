"""HWPX 미리보기 렌더 — PoC 결과 Phase 3 연기 (2026-05-02 T16).

Plan v2 Deviation 2 (`specs/2026-05-01-phase2-plan.md` Task 16) 결정에 따라
rhwp 통합은 Phase 3로 연기. 본 모듈은 인터페이스 placeholder로 남겨두며,
case06은 hwpx-editor만 사용 (라이브 미리보기 없이 운영자가 한글에서 수동 확인).

평가 결과 요약 (자세한 내용은 `specs/rhwp-poc-decision.md`):
- rhwp CLI: PNG/PDF 미지원 (SVG only), prebuilt binary 부재 → cargo from source 필요
- HOP: GUI cask만 존재, CLI 인터페이스 없음
- LibreOffice headless: 설치 시간/디스크 비용 큼, HWPX 호환성 검증 필요
- kordoc: HWPX → Markdown only (PDF 직접 미지원)

Phase 3 재진입 조건:
- rhwp CLI v2.0.0 (PDF 출력 추가)이 npm/cargo로 prebuilt 배포되거나
- HOP가 CLI 진입점 (`hop --export-pdf`)을 추가하거나
- LibreOffice 설치 비용 감수 + HWPX 변환 검증 1일 가능 시
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

PreviewFormat = Literal["png", "pdf"]
_VALID_FORMATS: frozenset[str] = frozenset({"png", "pdf"})

_FALLBACK_MESSAGE = (
    "rhwp integration deferred to Phase 3 (PoC failed). "
    "case06 will use fallback: hwpx-editor only (no live preview); "
    "operator opens output .hwpx in 한글 manually for visual confirmation. "
    "See specs/rhwp-poc-decision.md for full evaluation."
)


def render_preview(hwpx_path: Path | str, *, format: PreviewFormat = "pdf") -> Path:
    """HWPX → PNG/PDF 미리보기 렌더링.

    Phase 3로 연기된 기능이므로 호출 시 NotImplementedError를 raise한다.
    case06 시나리오는 본 함수를 호출하지 않고, hwpx-editor 결과 파일을 그대로
    제공한 뒤 운영자가 한글에서 수동 확인하는 fallback 경로를 따른다.

    Args:
        hwpx_path: 입력 HWPX 파일 경로 (현재는 검증만 수행하지 않고 즉시 raise)
        format: 출력 형식 ("png" 또는 "pdf"); 잘못된 값은 ValueError

    Raises:
        ValueError: format이 _VALID_FORMATS 외 값일 때
        NotImplementedError: 모든 정상 호출 (Phase 3 deferred). 메시지는
            fallback 경로와 결정 문서 위치를 명시.
    """
    if format not in _VALID_FORMATS:
        raise ValueError(f"unknown format: {format!r} (valid: {sorted(_VALID_FORMATS)})")

    # hwpx_path는 placeholder 시그니처를 위해 받지만 PoC 실패로 사용하지 않음.
    # Path 타입 정합성만 확인 (caller 실수 조기 발견).
    Path(hwpx_path)

    raise NotImplementedError(_FALLBACK_MESSAGE)
