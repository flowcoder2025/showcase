"""Case 01 — 거래처별 월별 매출 보고서 자동 생성."""
from pathlib import Path

from core.common import timer
from core.common.demo_logger import demo_logger
from core.excel import merger, pivot, writer

COLUMN_MAP = {"vendor": "거래처명", "date": "거래일", "amount": "금액"}


def run(input_dir: Path | str = "personas/sample_data/vendors",
        output_path: Path | str = "cases/case01_excel_vendor_report/output/report.xlsx") -> int:
    log = demo_logger("case01")
    input_dir = Path(input_dir)
    output_path = Path(output_path)

    with timer.measure(log, "거래처별 월별 매출 집계", before_minutes=180):
        merged = merger.merge_by_vendor(input_dir, column_map=COLUMN_MAP)
        pivoted = pivot.vendor_by_month(merged)
        writer.write_styled_report(pivoted, output_path, title="거래처별 월별 매출")

    log.success(f"완료: {output_path}")
    return 0


if __name__ == "__main__":
    run()
