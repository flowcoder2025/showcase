"""case07 — 영수증 일괄 OCR → 경비 정리 엑셀 (T38 ScenarioResult signature)."""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import openpyxl

from cases._protocols import Backends, ScenarioResult
from core.backends.factory import default_backends, safe_backends
from core.common import timer
from core.common.demo_logger import demo_logger
from core.common.safe_mode_v2 import is_safe
from core.ocr import receipt
from core.progress import ProgressEvent, done, emit, step

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_IN = _REPO_ROOT / "personas/sample_data/receipts"
_DEFAULT_OUT = Path(__file__).resolve().parent / "output"
_OUTPUT_NAME = "expense_report.xlsx"

EXPENSE_COLUMNS: tuple[str, ...] = (
    "거래일",
    "가맹점",
    "카테고리",
    "결제수단",
    "금액",
)

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

_PAYMENT_KEYWORDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("신용카드", re.compile(r"신용카드|카드결제|체크카드|VISA|MASTER")),
    ("삼성페이", re.compile(r"삼성페이")),
    ("네이버페이", re.compile(r"네이버페이|NPAY|N페이")),
    ("카카오페이", re.compile(r"카카오페이|KPAY|K페이")),
    ("현금", re.compile(r"현금|CASH")),
)


def _guess_payment(raw_text: str) -> str:
    for label, pattern in _PAYMENT_KEYWORDS:
        if pattern.search(raw_text):
            return label
    return ""


def _resolve_input_dir(input_dir: Path | None) -> Path:
    if input_dir is not None:
        return Path(input_dir)
    case_dir = Path(__file__).resolve().parent
    candidate = case_dir / "input"
    if candidate.exists() and any(p for p in candidate.iterdir() if not p.name.startswith(".")):
        return candidate
    return _DEFAULT_IN


def _collect_image_paths(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        return []
    return sorted(
        p
        for p in input_dir.iterdir()
        if p.is_file() and p.suffix.lower() in _IMAGE_EXTENSIONS and not p.name.startswith("_")
    )


def _write_xlsx(out_path: Path, rows: list[dict[str, Any]]) -> None:
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
    for prefix, category in _CATEGORY_BY_MERCHANT_PREFIX.items():
        if merchant.startswith(prefix):
            return category
    return "기타"


def run(
    *,
    input_dir: Path | None = None,
    output_dir: Path | None = None,
    backends: Backends | None = None,
    progress_cb: Callable[[ProgressEvent], None] | None = None,
    config: dict[str, Any] | None = None,
) -> ScenarioResult:
    """영수증 일괄 OCR → 경비 정리 엑셀."""
    out_dir = Path(output_dir) if output_dir else _DEFAULT_OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    _ = backends or (safe_backends() if is_safe() else default_backends())  # T40 wire-up
    _ = config or {}
    out_path = out_dir / _OUTPUT_NAME
    resolved_input = _resolve_input_dir(input_dir)
    image_paths = _collect_image_paths(resolved_input)

    log = demo_logger("case07_ocr_receipt_to_excel")
    processed = 0
    errors = 0
    rows: list[dict[str, Any]] = []
    receipts_meta: list[dict[str, Any]] = []
    per_image_ms: list[dict[str, Any]] = []

    label = f"영수증 OCR ({len(image_paths)}장)"
    total_images = len(image_paths)
    with timer.measure(log, label):
        for idx, img_path in enumerate(image_paths, start=1):
            emit(progress_cb, step("case07", img_path.name, idx, total_images))
            img_start = time.perf_counter()
            try:
                data = receipt.extract(img_path)
            except (ValueError, FileNotFoundError) as e:
                elapsed_ms = (time.perf_counter() - img_start) * 1000
                per_image_ms.append(
                    {"filename": img_path.name, "elapsed_ms": elapsed_ms, "error": True}
                )
                log.warning(f"[{img_path.name}] OCR failed: {e}")
                errors += 1
                continue

            elapsed_ms = (time.perf_counter() - img_start) * 1000
            per_image_ms.append({"filename": img_path.name, "elapsed_ms": elapsed_ms})

            merchant = data["merchant"]
            amount = int(data["amount"])
            rows.append(
                {
                    "거래일": data["date"],
                    "가맹점": merchant,
                    "카테고리": _guess_category(merchant),
                    "결제수단": _guess_payment(data.get("raw_text", "")),
                    "금액": amount,
                }
            )
            processed += 1
            receipts_meta.append(
                {
                    "filename": img_path.name,
                    "merchant": merchant,
                    "amount": amount,
                }
            )

    _write_xlsx(out_path, rows)

    if per_image_ms:
        avg_ms = sum(p["elapsed_ms"] for p in per_image_ms) / len(per_image_ms)
        log.info(f"평균 처리시간 {avg_ms:.0f}ms/장")

    log.success(f"처리 {processed}장 / 실패 {errors}장 → {out_path}")
    emit(progress_cb, done("case07", f"완료 — {processed}장 처리"))
    return {
        "case_id": "case07",
        "summary_text": f"영수증 {processed}장 처리 / 실패 {errors}장 → {out_path.name}",
        "output_files": [out_path],
        "metrics": {"processed": processed, "errors": errors},
        "failures": [],
        "extras": {"receipts": receipts_meta, "per_image_ms": per_image_ms},
    }


if __name__ == "__main__":
    run()
