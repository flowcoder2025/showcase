"""Case 01 — 거래처별 월별 매출 보고서 자동 생성 (T38: ScenarioResult signature)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from flowcoder_office_tools.backends.factory import default_backends, safe_backends
from flowcoder_office_tools.common import timer
from flowcoder_office_tools.common.demo_logger import demo_logger
from flowcoder_office_tools.common.safe_mode_v2 import is_safe
from flowcoder_office_tools.excel import merger, pivot, writer
from flowcoder_office_tools.progress import ProgressEvent
from flowcoder_office_tools.protocols import Backends, ScenarioResult

COLUMN_MAP = {"vendor": "거래처명", "date": "거래일", "amount": "금액"}

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_IN = _REPO_ROOT / "personas/sample_data/vendors"
_DEFAULT_OUT = Path(__file__).resolve().parent / "output"
_OUTPUT_NAME = "report.xlsx"


def run(
    *,
    input_dir: Path | None = None,
    output_dir: Path | None = None,
    backends: Backends | None = None,
    progress_cb: Callable[[ProgressEvent], None] | None = None,
    config: dict[str, Any] | None = None,
) -> ScenarioResult:
    in_dir = Path(input_dir) if input_dir else _DEFAULT_IN
    out_dir = Path(output_dir) if output_dir else _DEFAULT_OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    _ = backends or (safe_backends() if is_safe() else default_backends())  # T40 wire-up
    _ = config or {}
    output_path = out_dir / _OUTPUT_NAME

    log = demo_logger("case01")
    with timer.measure(log, "거래처별 월별 매출 집계", before_minutes=180):
        merged = merger.merge_by_vendor(in_dir, column_map=COLUMN_MAP)
        pivoted = pivot.vendor_by_month(merged)
        writer.write_styled_report(pivoted, output_path, title="거래처별 월별 매출")

    log.success(f"완료: {output_path}")
    n_vendors = int(pivoted.shape[0])
    total_rows = int(merged.shape[0])

    return {
        "case_id": "case01",
        "summary_text": f"거래처 {n_vendors}곳 월별 매출 보고서: {output_path.name}",
        "output_files": [output_path],
        "metrics": {"rows": total_rows, "vendors": n_vendors, "sheets": 1},
        "failures": [],
        "extras": {},
    }


if __name__ == "__main__":
    run()
