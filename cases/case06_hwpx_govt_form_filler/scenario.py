"""case06 — 정부지원사업 신청서 HWPX 자동 작성 (T38 ScenarioResult signature).

T38 정정: ``template_path`` 인자 → ``input_dir`` (안에 양식 파일) 또는
``config["template_path"]`` 직접 단일 파일. 기존 호출자는 config 패스스루.

Architecture
- Thin wrapper: scenario는 ``core.docgen.hwpx``만 호출. 외부 API 없음.
- 시각 미리보기 부재(T16 rhwp PoC 실패): ``hwpx.extract_text``로 값 포함 여부만
  검증한 뒤 한글 GUI 안내. ``render_preview`` / ``qlmanage`` 호출 안 함.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from cases._protocols import Backends, ScenarioResult
from core.backends.factory import default_backends, safe_backends
from core.common import timer
from core.common.demo_logger import demo_logger
from core.common.safe_mode_v2 import is_safe
from core.docgen import hwpx
from core.progress import ProgressEvent
from personas.sample_data.grant_data import AX_TRADING_GRANT, GrantApplication

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_IN = _REPO_ROOT / "personas/sample_data/forms"
_DEFAULT_OUT = Path(__file__).resolve().parent / "output"
_TEMPLATE_NAME = "grant_application_template.hwpx"
_OUTPUT_NAME = "grant_application_filled.hwpx"

_GRANT_TABLE_ID: str = "999000002"

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
    """GrantApplication → ``HwpxEditor.set_cell`` kwargs 리스트."""
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


def _resolve_template_path(input_dir: Path | None, cfg: dict[str, Any]) -> Path:
    """config["template_path"] 우선 → input_dir / _TEMPLATE_NAME → default."""
    explicit = cfg.get("template_path")
    if explicit is not None:
        return Path(explicit)
    if input_dir is not None:
        return Path(input_dir) / _TEMPLATE_NAME
    return _DEFAULT_IN / _TEMPLATE_NAME


def run(
    *,
    input_dir: Path | None = None,
    output_dir: Path | None = None,
    backends: Backends | None = None,
    progress_cb: Callable[[ProgressEvent], None] | None = None,
    config: dict[str, Any] | None = None,
) -> ScenarioResult:
    """HWPX 양식 채우기 + 검증."""
    out_dir = Path(output_dir) if output_dir else _DEFAULT_OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    _ = backends or (safe_backends() if is_safe() else default_backends())  # T40 wire-up
    cfg = config or {}
    payload: GrantApplication = cfg.get("data") or AX_TRADING_GRANT
    tpl = _resolve_template_path(input_dir, cfg)

    log = demo_logger("case06_hwpx_govt_form_filler")

    if not tpl.exists():
        raise FileNotFoundError(f"HWPX template not found: {tpl}")

    cell_fills = _build_cell_fills(payload)
    out_path = out_dir / _OUTPUT_NAME

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

    log.info(f"[OUTPUT] 채워진 양식: {out_path}")
    log.info("[ACTION] 시각 확인은 한글(Hancom Office)에서 결과 .hwpx를 열어 진행하세요")
    log.info("   (rhwp PoC 결과: specs/rhwp-poc-decision.md 참조 — 자동 미리보기 미지원)")

    return {
        "case_id": "case06",
        "summary_text": (
            f"양식 채움 {len(cell_fills)}/{len(cell_fills)} → {out_path.name}"
            if verification_passed
            else f"검증 실패 (누락 {len(missing_values)}건)"
        ),
        "output_files": [out_path],
        "metrics": {
            "fields_filled": len(cell_fills),
            "verification_passed": verification_passed,
            "elapsed_seconds": elapsed_seconds,
        },
        "failures": [{"value": v} for v in missing_values],
        "extras": {"missing_values": missing_values},
    }


if __name__ == "__main__":
    run()
