"""case05 — 견적서/거래명세서 일괄 생성 (docx + pdf).

Architecture
- thin wrapper: scenario.py가 ``core.docgen.{word, pdf}``만 호출 (외부 API 없음).
- per-request error isolation: word/pdf 일부 실패해도 다른 견적은 진행.
- column_map 강제: 다른 입력 컬럼 스키마에서도 동일 시나리오 재호출 가능.
- pandas read_excel 직접 호출 — ``core/excel/reader.py``에 read_excel 헬퍼 없음 (T2 deviation 동일).

NOTE: 외부 호출은 모듈 참조로 호출(safe_mode patch 격리):
    from core.docgen import pdf, word
    word.build_quote(...)
    pdf.md_to_pdf(...)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.common import timer
from core.common.demo_logger import demo_logger
from core.docgen import pdf as pdf_mod
from core.docgen import word as word_mod

COLUMN_MAP: dict[str, str] = {
    "request_id": "견적번호",
    "vendor": "거래처명",
    "name": "품목",
    "qty": "수량",
    "price": "단가",
    "due_date": "납기일",
}


def _make_md(vendor: str, items: list[dict[str, Any]], meta: dict[str, str]) -> str:
    """간단한 markdown — md_to_pdf 입력용. 견적서와 동일 데이터를 별도 표현."""
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


def run(
    input_path: Path | str | None = None,
    output_dir: Path | str | None = None,
    *,
    column_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """견적 요청 Excel → docx + pdf 일괄 생성.

    Returns
    -------
    summary : dict
        ``{"docx_count": int, "pdf_count": int, "errors": int,
           "requests": [{"request_id", "vendor", "n_items"}, ...]}``
    """
    log = demo_logger("case05_doc_quote_generator")
    case_dir = Path(__file__).parent
    cm = {**COLUMN_MAP, **(column_map or {})}

    if input_path is None:
        # 기본: case input/ → 없으면 personas 시드 fallback
        cand = case_dir / "input" / "quote_requests.xlsx"
        if not cand.exists():
            cand = Path("personas/sample_data/quote_requests.xlsx")
        input_path = cand

    if output_dir is None:
        output_dir = case_dir / "output"
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(Path(input_path))
    summary: dict[str, Any] = {
        "docx_count": 0,
        "pdf_count": 0,
        "errors": 0,
        "requests": [],
    }

    if df.empty:
        log.success("입력이 비어있어 생성할 견적서가 없습니다.")
        return summary

    # 견적번호별 group → 1 docx + 1 pdf
    grouped = df.groupby(cm["request_id"], sort=False)
    requests_list: list[dict[str, Any]] = summary["requests"]

    with timer.measure(log, "견적서 일괄 생성 (docx + pdf)", before_minutes=30):
        for request_id, group in grouped:
            request_id_str = str(request_id)
            vendor = str(group.iloc[0][cm["vendor"]])
            items = [
                {
                    "name": str(row[cm["name"]]),
                    "qty": int(row[cm["qty"]]),
                    "price": int(row[cm["price"]]),
                }
                for _, row in group.iterrows()
            ]
            meta = {"date": "2026-05-01", "quote_no": request_id_str}

            docx_built = False
            try:
                docx_path = out_dir / f"{request_id_str}.docx"
                word_mod.build_quote(
                    out_path=docx_path,
                    vendor=vendor,
                    items=items,
                    meta=meta,
                )
                summary["docx_count"] = int(summary["docx_count"]) + 1
                docx_built = True
            except Exception as e:  # noqa: BLE001 — per-request 실패 격리
                log.warning(f"docx failed for {request_id_str}: {e}")
                summary["errors"] = int(summary["errors"]) + 1

            if docx_built:
                # pdf via md
                md_text = _make_md(vendor, items, meta)
                md_path = out_dir / f"{request_id_str}.md"
                pdf_path = out_dir / f"{request_id_str}.pdf"
                try:
                    md_path.write_text(md_text, encoding="utf-8")
                    pdf_mod.md_to_pdf(md_path, pdf_path)
                    summary["pdf_count"] = int(summary["pdf_count"]) + 1
                except pdf_mod.MdToPdfError as e:
                    log.warning(f"pdf failed for {request_id_str}: {e}")
                    summary["errors"] = int(summary["errors"]) + 1
                except Exception as e:  # noqa: BLE001 — md write 등 보호
                    log.warning(f"pdf step failed for {request_id_str}: {e}")
                    summary["errors"] = int(summary["errors"]) + 1

            requests_list.append(
                {
                    "request_id": request_id_str,
                    "vendor": vendor,
                    "n_items": len(items),
                }
            )

    log.success(
        f"docx {summary['docx_count']}건 / pdf {summary['pdf_count']}건 / "
        f"실패 {summary['errors']}건"
    )
    return summary


if __name__ == "__main__":
    run()
