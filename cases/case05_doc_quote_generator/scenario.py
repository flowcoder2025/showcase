"""case05 — 견적서/거래명세서 일괄 생성 (docx + pdf) — T38 ScenarioResult signature."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import rich.markup
from flowcoder_office_tools.backends.factory import default_backends, safe_backends
from flowcoder_office_tools.common import timer
from flowcoder_office_tools.common.demo_logger import demo_logger
from flowcoder_office_tools.common.safe_mode_v2 import is_safe
from flowcoder_office_tools.docgen import pdf as pdf_mod
from flowcoder_office_tools.docgen import word as word_mod
from flowcoder_office_tools.progress import ProgressEvent
from flowcoder_office_tools.protocols import Backends, ScenarioResult

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_IN = _REPO_ROOT / "personas/sample_data"
_DEFAULT_OUT = Path(__file__).resolve().parent / "output"
_INPUT_NAME = "quote_requests.xlsx"

COLUMN_MAP: dict[str, str] = {
    "request_id": "견적번호",
    "vendor": "거래처명",
    "name": "품목",
    "qty": "수량",
    "price": "단가",
    "due_date": "납기일",
}


def _make_md(vendor: str, items: list[dict[str, Any]], meta: dict[str, str]) -> str:
    """간단한 markdown — md_to_pdf 입력용."""
    lines = [
        "# 견 적 서",
        "",
        f"- 견적번호: {meta['quote_no']}",
        f"- 작성일: {meta['date']}",
        f"- 거래처: {vendor}",
        "",
        "| 품목 | 수량 | 단가 | 금액 |",
        "|------|------|------|------|",
    ]
    total = 0
    for it in items:
        qty = int(it["qty"])
        price = int(it["price"])
        amount = qty * price
        total += amount
        lines.append(f"| {it['name']} | {qty:,} | {price:,} | {amount:,} |")
    lines.append("")
    lines.append(f"**합 계: {total:,}원**")
    return "\n".join(lines) + "\n"


def _resolve_input_path(input_dir: Path | None) -> Path:
    if input_dir is not None:
        return Path(input_dir) / _INPUT_NAME
    case_dir = Path(__file__).resolve().parent
    cand = case_dir / "input" / _INPUT_NAME
    if cand.exists():
        return cand
    return _DEFAULT_IN / _INPUT_NAME


def run(
    *,
    input_dir: Path | None = None,
    output_dir: Path | None = None,
    backends: Backends | None = None,
    progress_cb: Callable[[ProgressEvent], None] | None = None,
    config: dict[str, Any] | None = None,
) -> ScenarioResult:
    """견적 요청 Excel → docx + pdf 일괄 생성."""
    out_dir = Path(output_dir) if output_dir else _DEFAULT_OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    _ = backends or (safe_backends() if is_safe() else default_backends())  # T40 wire-up
    cfg = config or {}
    cm = {**COLUMN_MAP, **(cfg.get("column_map") or {})}
    input_path = _resolve_input_path(input_dir)

    log = demo_logger("case05_doc_quote_generator")
    df = pd.read_excel(input_path)
    docx_count = 0
    pdf_count = 0
    errors = 0
    requests_list: list[dict[str, Any]] = []
    output_files: list[Path] = []

    if df.empty:
        log.success("입력이 비어있어 생성할 견적서가 없습니다.")
        return {
            "case_id": "case05",
            "summary_text": "생성 대상 0건",
            "output_files": [],
            "metrics": {"docx_count": 0, "pdf_count": 0, "errors": 0},
            "failures": [],
            "extras": {"requests": requests_list},
        }

    grouped = df.groupby(cm["request_id"], sort=False)

    with timer.measure(log, "견적서 일괄 생성 (docx + pdf)", before_minutes=30):
        for request_id, group in grouped:
            request_id_str = str(request_id)
            vendor_raw = group.iloc[0][cm["vendor"]]
            vendor = "" if pd.isna(vendor_raw) else str(vendor_raw).strip()

            if not vendor:
                log.warning(f"[{request_id_str}] vendor empty — skipping")
                errors += 1
                continue

            items = [
                {
                    "name": str(row[cm["name"]]),
                    "qty": int(row[cm["qty"]]),
                    "price": int(row[cm["price"]]),
                }
                for _, row in group.iterrows()
            ]
            meta = {"date": date.today().isoformat(), "quote_no": request_id_str}

            vendor_safe = rich.markup.escape(vendor)
            log.info(f"[{request_id_str}] {vendor_safe} — {len(items)}개 품목 → docx + pdf")

            docx_built = False
            try:
                docx_path = out_dir / f"{request_id_str}.docx"
                word_mod.build_quote(
                    out_path=docx_path,
                    vendor=vendor,
                    items=items,
                    meta=meta,
                )
                docx_count += 1
                docx_built = True
                output_files.append(docx_path)
            except Exception as e:  # noqa: BLE001 — per-request 격리
                log.warning(f"[{request_id_str}] docx failed: {type(e).__name__}: {e}")
                errors += 1

            if docx_built:
                md_text = _make_md(vendor, items, meta)
                md_path = out_dir / f"{request_id_str}.md"
                pdf_path = out_dir / f"{request_id_str}.pdf"
                try:
                    md_path.write_text(md_text, encoding="utf-8")
                    pdf_mod.md_to_pdf(md_path, pdf_path)
                    pdf_count += 1
                    output_files.append(pdf_path)
                except pdf_mod.MdToPdfError as e:
                    log.warning(f"[{request_id_str}] pdf failed: {type(e).__name__}: {e}")
                    errors += 1
                except Exception as e:  # noqa: BLE001 — md write 등 보호
                    log.warning(f"[{request_id_str}] pdf step failed: {type(e).__name__}: {e}")
                    errors += 1

            requests_list.append(
                {
                    "request_id": request_id_str,
                    "vendor": vendor,
                    "n_items": len(items),
                }
            )

    log.success(f"docx {docx_count}건 / pdf {pdf_count}건 / 실패 {errors}건")
    return {
        "case_id": "case05",
        "summary_text": f"docx {docx_count}건 + pdf {pdf_count}건 / 실패 {errors}건",
        "output_files": output_files,
        "metrics": {
            "docx_count": docx_count,
            "pdf_count": pdf_count,
            "errors": errors,
        },
        "failures": [],
        "extras": {"requests": requests_list},
    }


if __name__ == "__main__":
    run()
