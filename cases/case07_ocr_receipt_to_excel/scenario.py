"""case07 — 영수증 일괄 OCR → 경비 정리 엑셀.

박과장 페르소나. 100장 영수증 이미지를 ``core.ocr.receipt.extract``로
일괄 OCR 후 회계SW 임포트 가능한 5컬럼 엑셀 생성.

Architecture
- Thin wrapper: scenario는 ``core.ocr.receipt.extract``만 호출. safe_mode 인터셉트는
  runner.py가 ``core.ocr.gemma.extract``를 patch하면 receipt가 자동으로 safe_dummy
  를 받아 ``[SAFE-FALLBACK]`` ReceiptData로 정규화 → scenario는 그대로 정상 처리.
- per-image 격리: ``ValueError``/``FileNotFoundError`` 발생 시 해당 영수증만 errors에
  카운트하고 나머지는 계속 처리 (시연 흐름 보호).
- 카테고리는 가맹점 prefix 룰베이스 매핑 — OCR 결과에 카테고리 필드가 없어도
  실용적인 분류 가능.
- ``_underscore`` prefix 파일은 자동 스킵 (시드 ground_truth.json 등).

R2-M2 risk: 합성 영수증은 self-OCR 자기충족 위험. 실 영수증 hold-out 검증 필요.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import openpyxl

from core.common import timer
from core.common.demo_logger import demo_logger
from core.ocr import receipt

# 출력 엑셀 컬럼 표준 (회계SW 임포트 호환)
EXPENSE_COLUMNS: tuple[str, ...] = (
    "거래일",
    "가맹점",
    "카테고리",
    "결제수단",
    "금액",
)

# personas 시드 디렉토리 — 테스트에서 monkeypatch 가능하도록 모듈 변수로 노출.
_DEFAULT_FALLBACK_DIR: Path = Path("personas/sample_data/receipts")

# 가맹점 prefix → 카테고리 룰. generate_receipts.py와 동기화 (R3-O1: 같은 매핑 재사용).
_CATEGORY_BY_MERCHANT_PREFIX: dict[str, str] = {
    "스타벅스": "커피",
    "이디야": "커피",
    "투썸": "커피",
    "할리스": "커피",
    "백다방": "커피",
    "맥도날드": "식사",
    "버거킹": "식사",
    "롯데마트": "장보기",
    "이마트": "장보기",
    "GS25": "편의점",
    "CU": "편의점",
    "세븐일레븐": "편의점",
}

_IMAGE_EXTENSIONS: frozenset[str] = frozenset({".png", ".jpg", ".jpeg"})


def run(
    input_dir: Path | str | None = None,
    output_path: Path | str | None = None,
) -> dict[str, Any]:
    """영수증 일괄 OCR → 경비 정리 엑셀.

    Args:
        input_dir: 영수증 이미지 디렉토리. ``None`` → ``cases/case07.../input/``,
            비어 있으면 ``personas/sample_data/receipts/`` fallback.
        output_path: 결과 xlsx 경로. ``None`` → ``cases/case07.../output/expense_report.xlsx``.

    Returns:
        ``{"processed": int, "errors": int, "rows": list[dict]}``.
    """
    log = demo_logger("case07_ocr_receipt_to_excel")
    case_dir = Path(__file__).parent

    resolved_input = _resolve_input_dir(input_dir, case_dir)
    if output_path is not None:
        out_path = Path(output_path)
    else:
        out_path = case_dir / "output" / "expense_report.xlsx"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    image_paths = _collect_image_paths(resolved_input)

    summary: dict[str, Any] = {"processed": 0, "errors": 0, "rows": []}
    rows: list[dict[str, Any]] = []

    label = f"영수증 OCR ({len(image_paths)}장)"
    with timer.measure(log, label):
        for img_path in image_paths:
            try:
                data = receipt.extract(img_path)
            except (ValueError, FileNotFoundError) as e:
                log.warning(f"[{img_path.name}] OCR failed: {e}")
                summary["errors"] += 1
                continue

            merchant = data["merchant"]
            amount = int(data["amount"])
            rows.append(
                {
                    "거래일": data["date"],
                    "가맹점": merchant,
                    "카테고리": _guess_category(merchant),
                    # OCR 응답에 결제수단 없음 — T11.5에서 items 분석 기반 추출 후속.
                    "결제수단": "",
                    "금액": amount,
                }
            )
            summary["processed"] += 1
            summary["rows"].append(
                {
                    "filename": img_path.name,
                    "merchant": merchant,
                    "amount": amount,
                }
            )

    _write_xlsx(out_path, rows)

    log.success(f"처리 {summary['processed']}장 / 실패 {summary['errors']}장 → {out_path}")
    return summary


# -- internal helpers -------------------------------------------------------


def _resolve_input_dir(input_dir: Path | str | None, case_dir: Path) -> Path:
    """input_dir 결정: 명시값 > case input/ > personas fallback."""
    if input_dir is not None:
        return Path(input_dir)
    candidate = case_dir / "input"
    if candidate.exists() and any(p for p in candidate.iterdir() if not p.name.startswith(".")):
        return candidate
    return _DEFAULT_FALLBACK_DIR


def _collect_image_paths(input_dir: Path) -> list[Path]:
    """이미지 확장자 + non-underscore prefix만 수집. 결정적 정렬."""
    if not input_dir.exists():
        return []
    return sorted(
        p
        for p in input_dir.iterdir()
        if p.is_file() and p.suffix.lower() in _IMAGE_EXTENSIONS and not p.name.startswith("_")
    )


def _write_xlsx(out_path: Path, rows: list[dict[str, Any]]) -> None:
    """경비 정리 시트 생성. 헤더 + rows."""
    wb = openpyxl.Workbook()
    ws = wb.active
    if ws is None:  # pragma: no cover — openpyxl 계약상 항상 존재
        raise RuntimeError("openpyxl workbook has no active sheet")
    ws.title = "경비 정리"
    ws.append(list(EXPENSE_COLUMNS))
    for row in rows:
        ws.append([row[col] for col in EXPENSE_COLUMNS])
    wb.save(str(out_path))


def _guess_category(merchant: str) -> str:
    """가맹점 prefix 매칭 → 카테고리. 매칭 실패 시 '기타'."""
    for prefix, category in _CATEGORY_BY_MERCHANT_PREFIX.items():
        if merchant.startswith(prefix):
            return category
    return "기타"


if __name__ == "__main__":
    run()
