"""case06 — 정부지원사업 신청서 HWPX 자동 작성.

김사장 페르소나. AX상사 신청 데이터를 ``personas/sample_data/forms/
grant_application_template.hwpx`` (8행×2열) 양식의 우측 값 컬럼에 자동 채워
``cases/case06.../output/`` 에 결과 .hwpx를 저장한다.

Architecture
- Thin wrapper: scenario는 ``core.docgen.hwpx``만 호출. 외부 API 없음.
  ``safe_mode.intercept`` 호출하지 않는다 — 어차피 외부 API가 없으므로
  ``safe`` 인자는 informational(메타 표기에만 영향).
- 시각 미리보기 부재: T16 rhwp PoC 실패(`specs/rhwp-poc-decision.md`)로
  ``core.docgen.hwp_preview.render_preview`` 는 ``NotImplementedError`` 를
  raise한다. 따라서 case06은 ``render_preview``를 절대 호출하지 않는다.
  ``qlmanage`` 폴백도 시도하지 않는다(.hwpx mime 미인식 — 결정 문서 참조).
  대신 채워진 .hwpx 파일을 디스크에 저장하고 ``hwpx.extract_text``로
  값 포함 여부를 검증한 뒤, "한글에서 열어 시각 확인"을 데모로거로 안내한다.
- 채움 데이터는 ``personas.sample_data.grant_data.AX_TRADING_GRANT``
  (TypedDict). 양식 좌측 라벨 행 순서와 1:1 매칭.

Module-call convention: ``from core.docgen import hwpx; hwpx.fill_form(...)``.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from core.common import timer
from core.common.demo_logger import demo_logger
from core.docgen import hwpx
from personas.sample_data.grant_data import AX_TRADING_GRANT, GrantApplication

# 양식 fixture 경로 — 테스트에서 monkeypatch 가능하도록 모듈 변수로 노출.
_DEFAULT_TEMPLATE_PATH: Path = Path("personas/sample_data/forms/grant_application_template.hwpx")

# build_grant_template.py가 주입한 8행 표의 id. 행 순서는 GRANT_LABELS와 동일.
_GRANT_TABLE_ID: str = "999000002"

# 양식 행 순서 → GrantApplication 키 매핑. 정수/문자열을 표시용 문자열로 변환.
_FIELD_ORDER: tuple[str, ...] = (
    "company_name",
    "ceo_name",
    "biznum",
    "business_area",
    "grant_amount",
    "annual_revenue",
    "employee_count",
    "application_date",
)


def _format_field(key: str, value: Any) -> str:
    """GrantApplication 값을 양식 셀에 들어갈 표시용 문자열로 변환."""
    if key in {"grant_amount", "annual_revenue"}:
        return f"{int(value):,}원"
    if key == "employee_count":
        return f"{int(value)}명"
    return str(value)


def _build_cell_fills(
    data: GrantApplication, *, table_id: str = _GRANT_TABLE_ID
) -> list[dict[str, Any]]:
    """GrantApplication → ``HwpxEditor.set_cell`` kwargs 리스트.

    각 항목은 ``{table_id, col, row, text, label}``. ``label`` 은 hwpx-editor
    스킬 stderr 진단용(채울 셀이 어떤 라벨인지 알려줌, 동작에 영향 없음).
    """
    cell_fills: list[dict[str, Any]] = []
    for row_idx, key in enumerate(_FIELD_ORDER):
        if key not in data:
            raise ValueError(f"grant data missing required field: {key!r}")
        value = data[key]  # type: ignore[literal-required]
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValueError(f"grant data field {key!r} is empty/blank")
        cell_fills.append(
            {
                "table_id": table_id,
                "col": 1,
                "row": row_idx,
                "text": _format_field(key, value),
                "label": key,
            }
        )
    return cell_fills


def run(
    template_path: Path | str | None = None,
    output_dir: Path | str | None = None,
    *,
    safe: bool = False,
    data: GrantApplication | None = None,
) -> dict[str, Any]:
    """HWPX 양식 채우기 + 검증.

    Args:
        template_path: 입력 .hwpx 양식. ``None`` → ``_DEFAULT_TEMPLATE_PATH``.
        output_dir: 결과 디렉토리. ``None`` → ``cases/case06.../output/``.
        safe: 외부 API가 없는 케이스이므로 동작에 영향 없음 (메타 표기용).
        data: 채울 데이터. ``None`` → ``AX_TRADING_GRANT``.

    Returns:
        ``{"output_path": str, "fields_filled": int, "verification_passed": bool,
           "elapsed_seconds": float, "missing_values": list[str]}``.

    Raises:
        FileNotFoundError: ``template_path`` 가 존재하지 않을 때.
        ValueError: ``data`` 에 필수 필드가 비어있거나 누락됐을 때.
    """
    log = demo_logger("case06_hwpx_govt_form_filler")
    case_dir = Path(__file__).parent

    tpl = Path(template_path) if template_path is not None else _DEFAULT_TEMPLATE_PATH
    out_dir = Path(output_dir) if output_dir is not None else (case_dir / "output")
    out_dir.mkdir(parents=True, exist_ok=True)

    if not tpl.exists():
        raise FileNotFoundError(f"HWPX template not found: {tpl}")

    payload: GrantApplication = data if data is not None else AX_TRADING_GRANT

    # 사전 검증 — fill_form 진입 전에 필수 필드 누락을 한번에 차단.
    cell_fills = _build_cell_fills(payload)

    out_path = out_dir / "grant_application_filled.hwpx"

    run_start = time.perf_counter()
    with timer.measure(log, "정부지원사업 신청서 HWPX 자동 채움", before_minutes=30):
        log.info(
            f"양식: {tpl.name} → {len(cell_fills)}개 필드 자동 채움 "
            f"(회사명={payload['company_name']})"
        )
        hwpx.fill_form(
            template_path=tpl,
            out_path=out_path,
            cell_fills=cell_fills,
        )

    # 검증: extract_text 로 모든 채운 값이 결과 파일에 남아있는지 확인.
    extracted = hwpx.extract_text(out_path)
    missing_values: list[str] = []
    for fill in cell_fills:
        text = str(fill["text"])
        if text not in extracted:
            missing_values.append(text)

    verification_passed = not missing_values
    elapsed_seconds = time.perf_counter() - run_start

    if verification_passed:
        log.success(f"채움 완료 ({len(cell_fills)}/{len(cell_fills)} 필드) → {out_path}")
    else:
        log.warning(
            f"검증 실패: {len(missing_values)}개 값이 결과 파일에서 누락 ({missing_values})"
        )

    # rhwp PoC 실패로 시각 미리보기 자동화 미지원 — 운영자가 한글 GUI에서 확인.
    log.info(f"[OUTPUT] 채워진 양식: {out_path}")
    log.info("[ACTION] 시각 확인은 한글(Hancom Office)에서 결과 .hwpx를 열어 진행하세요")
    log.info("   (rhwp PoC 결과: specs/rhwp-poc-decision.md 참조 — 자동 미리보기 미지원)")

    return {
        "output_path": str(out_path),
        "fields_filled": len(cell_fills),
        "verification_passed": verification_passed,
        "elapsed_seconds": elapsed_seconds,
        "missing_values": missing_values,
    }


if __name__ == "__main__":
    run()
