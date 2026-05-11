"""case03 — 견적 메일 일괄 발송 (개인화 + PDF 첨부) — T38 ScenarioResult signature.

Architecture (T38 시그니처 정식화 후에도 보존):
- thin wrapper: scenario.py가 ``core.messaging.email`` + ``core.docgen.{pdf, template}`` 만 호출.
- 단일 patch point: ``email.send`` (T7b 결정 — INTERCEPT_TARGETS["gmail"]).
- per-request error isolation: PDF 실패 시 첨부 없이 발송, send 실패 / build 실패 시 errors+1.
- column_map 강제: 다른 입력 컬럼 스키마에서도 동일 시나리오 재호출 가능.
- XSS 방어: HTML 본문은 ``email.build_html_body`` 사용 (autoescape, T7a.5).

NOTE: 외부 호출은 모듈 참조로 호출(safe_mode patch 격리)::

    from core.docgen import pdf, template
    from core.messaging import email
    email.send(...)
    pdf.md_to_pdf(...)
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd
import rich.markup

from cases._protocols import Backends, ScenarioResult
from core.backends.factory import default_backends, safe_backends
from core.common import timer
from core.common.demo_logger import demo_logger
from core.common.safe_mode_v2 import is_safe
from core.docgen import pdf as pdf_mod
from core.docgen import template as tmpl_mod
from core.messaging import email as email_mod
from core.progress import ProgressEvent

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_IN = _REPO_ROOT / "personas/sample_data"
_DEFAULT_OUT = Path(__file__).resolve().parent / "output"
_INPUT_NAME = "quote_dispatch_list.xlsx"

COLUMN_MAP: dict[str, str] = {
    "vendor": "거래처명",
    "contact": "담당자",
    "to": "이메일",
    "quote_no": "견적번호",
    "summary": "품목요약",
    "amount": "예상금액",
    "history": "과거거래",
}

EMAIL_HTML_TEMPLATE = """\
<p>안녕하세요, {{ vendor }} {{ contact }}님.</p>
<p>요청하신 <strong>{{ summary }}</strong> 관련 견적서를 첨부합니다.</p>
<ul>
  <li>견적번호: {{ quote_no }}</li>
  <li>예상금액: {{ amount_str }}원</li>
</ul>
<p>지난 거래 메모: <em>{{ history }}</em></p>
<p>감사합니다.</p>
"""

EMAIL_TEXT_TEMPLATE = """\
안녕하세요, {{ vendor }} {{ contact }}님.

요청하신 {{ summary }} 관련 견적서를 첨부합니다.
- 견적번호: {{ quote_no }}
- 예상금액: {{ amount_str }}원

지난 거래 메모: {{ history }}

감사합니다.
"""


def _build_quote_md(ctx: dict[str, str]) -> str:
    """간단한 견적서 markdown — md_to_pdf 입력용."""
    return (
        f"# 견 적 서 {ctx['quote_no']}\n\n"
        f"- 거래처: {ctx['vendor']}\n"
        f"- 담당자: {ctx['contact']}\n"
        f"- 품목: {ctx['summary']}\n"
        f"- 예상금액: {ctx['amount_str']}원\n"
    )


def _resolve_input_path(input_dir: Path | None) -> Path:
    """T38: input_dir / quote_dispatch_list.xlsx; default falls back to case input/ then personas."""  # noqa: E501
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
    """50건 일괄 발송: 단순 PDF 생성 + 개인화 메일 + 첨부."""
    out_dir = Path(output_dir) if output_dir else _DEFAULT_OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    _ = backends or (safe_backends() if is_safe() else default_backends())  # T40 wire-up
    cfg = config or {}
    column_map = cfg.get("column_map")
    cm = {**COLUMN_MAP, **(column_map or {})}
    input_path = _resolve_input_path(input_dir)

    log = demo_logger("case03_email_quote_dispatch")
    df = pd.read_excel(input_path)
    built = 0
    sent_count = 0
    errors = 0
    pdf_failed = 0
    transports: dict[str, int] = {}
    rows_list: list[dict[str, Any]] = []
    output_pdfs: list[Path] = []

    if df.empty:
        log.success("입력이 비어있어 발송할 견적이 없습니다.")
        return {
            "case_id": "case03",
            "summary_text": "발송 대상 0건",
            "output_files": [],
            "metrics": {"built": 0, "sent": 0, "errors": 0, "pdf_failed": 0},
            "failures": [],
            "extras": {"transports": transports, "rows": rows_list},
        }

    with timer.measure(log, "견적 메일 일괄 발송", before_minutes=60):
        for _, row in df.iterrows():
            quote_no = str(row[cm["quote_no"]])
            vendor = str(row[cm["vendor"]]).strip()
            contact = str(row[cm["contact"]])
            to_addr = str(row[cm["to"]])
            amount_raw = row[cm["amount"]]
            if pd.isna(amount_raw):
                log.warning(f"[{quote_no}] amount is NaN — using 0")
                amount_int = 0
            else:
                try:
                    amount_int = int(amount_raw)
                except (ValueError, TypeError):
                    log.warning(f"[{quote_no}] amount invalid ({amount_raw!r}) — using 0")
                    amount_int = 0
            ctx: dict[str, str] = {
                "vendor": vendor,
                "contact": contact,
                "summary": str(row[cm["summary"]]),
                "amount_str": f"{amount_int:,}",
                "quote_no": quote_no,
                "history": str(row[cm["history"]]),
            }

            md_path = out_dir / f"{quote_no}.md"
            pdf_target = out_dir / f"{quote_no}.pdf"
            pdf_ok = False
            try:
                md_path.write_text(_build_quote_md(ctx), encoding="utf-8")
                pdf_mod.md_to_pdf(md_path, pdf_target)
                pdf_ok = True
                output_pdfs.append(pdf_target)
            except pdf_mod.MdToPdfError as e:
                log.warning(f"[{quote_no}] pdf failed: {type(e).__name__}: {e}")
                pdf_failed += 1
            except Exception as e:  # noqa: BLE001 — pdf 단계 보호 (md write 등)
                log.warning(f"[{quote_no}] pdf step failed: {type(e).__name__}: {e}")
                pdf_failed += 1

            try:
                html_body = email_mod.build_html_body(EMAIL_HTML_TEMPLATE, ctx)
                text_body = tmpl_mod.render_string(EMAIL_TEXT_TEMPLATE, ctx)
                attachments: list[Path] = []
                if pdf_ok and pdf_target.exists():
                    attachments.append(pdf_target)

                msg = email_mod.build_message(
                    to=to_addr,
                    subject=f"[{quote_no}] 견적서 송부 - {vendor}",
                    body_text=text_body,
                    body_html=html_body,
                    attachments=attachments,
                )
                built += 1

                result = email_mod.send(msg)
                if isinstance(result, dict) and result.get("_safe") is True:
                    transport_name = "safe-fallback"
                    sent_flag = False
                else:
                    transport_name = str(result["transport"])
                    sent_flag = bool(result["sent"])
                if sent_flag or transport_name == "safe-fallback":
                    sent_count += 1
                transports[transport_name] = transports.get(transport_name, 0) + 1

                vendor_safe = rich.markup.escape(vendor)
                log.info(f"[{quote_no}] {vendor_safe} → {to_addr} ({transport_name})")
                rows_list.append(
                    {
                        "quote_no": quote_no,
                        "vendor": vendor,
                        "to": to_addr,
                        "transport": transport_name,
                    }
                )
            except Exception as e:  # noqa: BLE001 — per-request 격리
                log.warning(f"[{quote_no}] failed: {type(e).__name__}: {e}")
                errors += 1

    log.success(f"빌드 {built}건 / 발송 {sent_count}건 / PDF 실패 {pdf_failed}건 / 에러 {errors}건")
    return {
        "case_id": "case03",
        "summary_text": f"발송 {sent_count}건 / 빌드 {built}건 / 에러 {errors}건",
        "output_files": output_pdfs,
        "metrics": {
            "built": built,
            "sent": sent_count,
            "errors": errors,
            "pdf_failed": pdf_failed,
        },
        "failures": [],
        "extras": {"transports": transports, "rows": rows_list},
    }


if __name__ == "__main__":
    run()
