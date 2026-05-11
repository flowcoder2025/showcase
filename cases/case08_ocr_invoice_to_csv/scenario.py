"""case08 — 세금계산서 일괄 OCR → 회계 CSV (T38 ScenarioResult signature)."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from flowcoder_office_tools.backends.factory import default_backends, safe_backends
from flowcoder_office_tools.common import timer
from flowcoder_office_tools.common.demo_logger import demo_logger
from flowcoder_office_tools.common.safe_mode_v2 import is_safe
from flowcoder_office_tools.ocr import invoice
from flowcoder_office_tools.progress import ProgressEvent, done, emit, step
from flowcoder_office_tools.protocols import Backends, ScenarioResult

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_IN = _REPO_ROOT / "personas/sample_data/invoices_scanned"
_DEFAULT_OUT = Path(__file__).resolve().parent / "output"

_IMAGE_EXTENSIONS: frozenset[str] = frozenset({".png", ".jpg", ".jpeg"})


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


def _classify_failure(data: invoice.InvoiceData) -> str | None:
    """추가 검증 게이트 — biznum 모듈러스 + VAT 일치 (±1)."""
    if not invoice.validate_biznum(data["supplier_biznum"]):
        return f"supplier_biznum invalid: {data['supplier_biznum']!r}"
    if not invoice.validate_biznum(data["buyer_biznum"]):
        return f"buyer_biznum invalid: {data['buyer_biznum']!r}"
    supply = int(data["total_supply"])
    vat = int(data["total_vat"])
    expected = supply // 10
    if vat != 0 and abs(vat - expected) > 1:
        return f"vat mismatch: vat={vat:,} expected {expected:,}±1 (supply={supply:,})"
    return None


def run(
    *,
    input_dir: Path | None = None,
    output_dir: Path | None = None,
    backends: Backends | None = None,
    progress_cb: Callable[[ProgressEvent], None] | None = None,
    config: dict[str, Any] | None = None,
) -> ScenarioResult:
    """세금계산서 일괄 OCR → 회계 CSV (utf-8 + cp949) + validation_failures.json."""
    out_dir = Path(output_dir) if output_dir else _DEFAULT_OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    _ = backends or (safe_backends() if is_safe() else default_backends())  # T40 wire-up
    _ = config or {}
    resolved_input = _resolve_input_dir(input_dir)
    image_paths = _collect_image_paths(resolved_input)

    log = demo_logger("case08_ocr_invoice_to_csv")
    verified: list[invoice.InvoiceData] = []
    failures: list[dict[str, Any]] = []
    per_image_ms: list[dict[str, Any]] = []

    label = f"세금계산서 OCR ({len(image_paths)}장)"
    total_images = len(image_paths)
    run_start = time.perf_counter()
    with timer.measure(log, label):
        for idx, img_path in enumerate(image_paths, start=1):
            emit(progress_cb, step("case08", img_path.name, idx, total_images))
            img_start = time.perf_counter()
            try:
                data = invoice.extract(img_path)
            except (ValueError, FileNotFoundError) as e:
                elapsed_ms = (time.perf_counter() - img_start) * 1000
                per_image_ms.append(
                    {"filename": img_path.name, "elapsed_ms": elapsed_ms, "error": True}
                )
                log.warning(f"[{img_path.name}] OCR/validation failed: {e}")
                failures.append({"filename": img_path.name, "stage": "extract", "reason": str(e)})
                continue

            elapsed_ms = (time.perf_counter() - img_start) * 1000
            per_image_ms.append({"filename": img_path.name, "elapsed_ms": elapsed_ms})

            failure_reason = _classify_failure(data)
            if failure_reason is not None:
                failures.append(
                    {
                        "filename": img_path.name,
                        "stage": "validate",
                        "reason": failure_reason,
                        "invoice_no": data["invoice_no"],
                        "supplier_biznum": data["supplier_biznum"],
                        "buyer_biznum": data["buyer_biznum"],
                    }
                )
                log.warning(f"[{img_path.name}] post-validation failed: {failure_reason}")
                continue

            verified.append(data)

    elapsed_seconds = time.perf_counter() - run_start

    utf8_path = out_dir / "invoices_utf8.csv"
    cp949_path = out_dir / "invoices_cp949.csv"
    failures_path = out_dir / "validation_failures.json"

    invoice.to_accounting_csv(verified, utf8_path, encoding="utf-8", bom=True)
    invoice.to_accounting_csv(verified, cp949_path, encoding="cp949")
    failures_path.write_text(
        json.dumps(failures, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if per_image_ms:
        avg_ms = sum(p["elapsed_ms"] for p in per_image_ms) / len(per_image_ms)
        log.info(f"평균 처리시간 {avg_ms:.0f}ms/장")

    processed = len(image_paths)
    failure_rate = (len(failures) / processed) if processed > 0 else 0.0
    quality_warning = processed > 0 and failure_rate >= 0.5
    if quality_warning:
        log.warning("=" * 60)
        log.warning(f"품질 경고: 실패율 {failure_rate:.0%} ({len(failures)}/{processed}) >= 50%")
        log.warning("OCR 품질이 정상 범위를 벗어났습니다. 다음을 확인하세요:")
        log.warning("  1. 이미지 해상도/스캔 품질 (블러, 회전, 잘림)")
        log.warning("  2. Gemma 4 모델 가중치 (재시작/리로드 시도)")
        log.warning("  3. 시연 흐름이 우선이면 DEMO_SAFE=1 로 재실행")
        log.warning("=" * 60)

    log.success(f"처리 {processed}장 / 검증통과 {len(verified)} / 실패 {len(failures)} → {out_dir}")
    emit(progress_cb, done("case08", f"완료 — {processed}장 / 검증 {len(verified)}"))

    return {
        "case_id": "case08",
        "summary_text": (f"세금계산서 {processed}장 / 검증 {len(verified)} / 실패 {len(failures)}"),
        "output_files": [utf8_path, cp949_path, failures_path],
        "metrics": {
            "processed": processed,
            "verified": len(verified),
            "failed": len(failures),
            "failure_rate": failure_rate,
            "quality_warning": quality_warning,
            "elapsed_seconds": elapsed_seconds,
        },
        "failures": failures,
        "extras": {
            "invoices": [dict(d) for d in verified],
            "per_image_ms": per_image_ms,
        },
    }


if __name__ == "__main__":
    run()
