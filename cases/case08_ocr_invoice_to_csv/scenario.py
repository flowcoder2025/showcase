"""case08 — 세금계산서 일괄 OCR → 회계 CSV (Gemma 4 E4B).

박과장 페르소나. 30장 세금계산서 이미지를 ``core.ocr.invoice.extract``로 일괄 OCR 후
한국 사업자번호 모듈러스 체크섬·부가세 일치 여부로 검증해 verified/failed로 분리한 뒤
회계SW 임포트용 CSV를 utf-8(BOM)·cp949 두 인코딩으로 동시 export.

Architecture
- Thin wrapper: scenario는 ``core.ocr.invoice.extract``만 호출. safe_mode 인터셉트는
  runner.py가 ``core.ocr.gemma.extract``를 patch하면 invoice가 자동으로 safe placeholder
  를 받아 정규화된 ``InvoiceData`` (체크섬 통과 placeholder biznum 포함) 반환.
- per-invoice 격리: ``ValueError``/``FileNotFoundError`` 발생 시 해당 세금계산서만
  ``failed`` 리스트에 기록하고 나머지는 계속 처리 (시연 흐름 보호).
- ``_underscore`` prefix 파일은 자동 스킵 (시드 ground_truth.json 등).
- 검증 게이트:
    1. ``invoice.extract`` 자체가 biznum 체크섬·VAT 일치를 강제 — 실패 시 ValueError.
    2. scenario는 추가로 ``validate_biznum`` 양측을 다시 한 번 호출
       (safe-fallback placeholder가 들어와도 통과 가능 — placeholder는 valid biznum).
    3. ``vat == supply // 10 OR vat == 0`` 게이트 (면세 지원).
- dual export: utf-8 + BOM (Excel friendly) / cp949 (legacy 회계SW).
- ``validation_failures.json``: failed 리스트를 그대로 직렬화 — empty 리스트일 때도 작성.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from core.common import timer
from core.common.demo_logger import demo_logger
from core.ocr import invoice

# personas 시드 디렉토리 — 테스트에서 monkeypatch 가능하도록 모듈 변수로 노출.
_DEFAULT_FALLBACK_DIR: Path = Path("personas/sample_data/invoices_scanned")

_IMAGE_EXTENSIONS: frozenset[str] = frozenset({".png", ".jpg", ".jpeg"})


def run(
    input_dir: Path | str | None = None,
    output_dir: Path | str | None = None,
) -> dict[str, Any]:
    """세금계산서 일괄 OCR → 회계 CSV (utf-8 + cp949).

    Args:
        input_dir: 세금계산서 이미지 디렉토리. ``None`` → ``cases/case08.../input/``,
            비어 있으면 ``personas/sample_data/invoices_scanned/`` fallback.
        output_dir: 결과 디렉토리. ``None`` → ``cases/case08.../output/``.

    Returns:
        ``{"processed": int, "verified": int, "failed": int,
           "failure_rate": float, "quality_warning": bool,
           "elapsed_seconds": float, "outputs": list[str], "per_image_ms": list[dict],
           "failures": list[dict]}``. ``quality_warning=True`` 시 운영자가 DEMO_SAFE=1
        재실행을 검토해야 한다 (auto-force_safe는 의도적으로 안 함 — partial-success
        real run을 silent swap 하면 OCR 품질 저하를 운영자가 못 알아챔).
    """
    log = demo_logger("case08_ocr_invoice_to_csv")
    case_dir = Path(__file__).parent

    resolved_input = _resolve_input_dir(input_dir, case_dir)
    out_dir = Path(output_dir) if output_dir is not None else (case_dir / "output")
    out_dir.mkdir(parents=True, exist_ok=True)

    image_paths = _collect_image_paths(resolved_input)

    verified: list[invoice.InvoiceData] = []
    failures: list[dict[str, Any]] = []
    per_image_ms: list[dict[str, Any]] = []

    label = f"세금계산서 OCR ({len(image_paths)}장)"
    run_start = time.perf_counter()
    with timer.measure(log, label):
        for img_path in image_paths:
            img_start = time.perf_counter()
            try:
                data = invoice.extract(img_path)
            except (ValueError, FileNotFoundError) as e:
                elapsed_ms = (time.perf_counter() - img_start) * 1000
                per_image_ms.append(
                    {"filename": img_path.name, "elapsed_ms": elapsed_ms, "error": True}
                )
                log.warning(f"[{img_path.name}] OCR/validation failed: {e}")
                failures.append(
                    {
                        "filename": img_path.name,
                        "stage": "extract",
                        "reason": str(e),
                    }
                )
                continue

            elapsed_ms = (time.perf_counter() - img_start) * 1000
            per_image_ms.append({"filename": img_path.name, "elapsed_ms": elapsed_ms})

            # 추가 검증 (extract가 이미 강제하지만 시연 시 명시적으로 한 번 더 통과).
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

    # >=50% 실패 시 prominent warning (auto-force_safe는 일부러 안 함 — partial-success
    # real run을 silent로 캐시 응답으로 swap하면 운영자가 OCR 품질 저하를 못 알아챔).
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

    return {
        "processed": processed,
        "verified": len(verified),
        "failed": len(failures),
        "failure_rate": failure_rate,
        "quality_warning": quality_warning,
        "elapsed_seconds": elapsed_seconds,
        "outputs": [str(utf8_path), str(cp949_path), str(failures_path)],
        "per_image_ms": per_image_ms,
        "failures": failures,
    }


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


def _classify_failure(data: invoice.InvoiceData) -> str | None:
    """추가 검증 게이트.

    invoice.extract가 이미 biznum/VAT를 강제하지만, 시연 직전 한 번 더 명시적으로 검증해
    safe-fallback이 아닌 정상 경로의 결과만 verified로 분류한다. safe-fallback placeholder는
    valid biznum + vat=0 조건을 만족하므로 통과한다(시연 흐름 보호).

    Returns:
        실패 사유 문자열 또는 통과 시 ``None``.
    """
    if not invoice.validate_biznum(data["supplier_biznum"]):
        return f"supplier_biznum invalid: {data['supplier_biznum']!r}"
    if not invoice.validate_biznum(data["buyer_biznum"]):
        return f"buyer_biznum invalid: {data['buyer_biznum']!r}"
    supply = int(data["total_supply"])
    vat = int(data["total_vat"])
    expected = supply // 10
    # R2-H3: ±1원 허용 (banker's rounding 차이) — invoice._validate_and_normalize와 동일 기준.
    if vat != 0 and abs(vat - expected) > 1:
        return f"vat mismatch: vat={vat:,} expected {expected:,}±1 (supply={supply:,})"
    return None


if __name__ == "__main__":
    run()
