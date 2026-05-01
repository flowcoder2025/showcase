"""case03 — 견적 메일 일괄 발송 (개인화 + PDF 첨부).

Architecture
- thin wrapper: scenario.py가 ``core.messaging.email`` + ``core.docgen.{pdf, template}`` 만 호출.
- 단일 patch point: ``email.send`` (T7b 결정 — INTERCEPT_TARGETS["gmail"]).
  ``send`` 만 patch 되어도 모든 외부 호출이 격리된다 (gmail_api/smtp internal helper 미포함).
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

from pathlib import Path
from typing import Any

import pandas as pd
import rich.markup

from core.common import timer
from core.common.demo_logger import demo_logger
from core.docgen import pdf as pdf_mod
from core.docgen import template as tmpl_mod
from core.messaging import email as email_mod

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


def run(
    input_path: Path | str | None = None,
    output_dir: Path | str | None = None,
    *,
    column_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """50건 일괄 발송: 단순 PDF 생성 + 개인화 메일 + 첨부.

    Returns
    -------
    summary : dict
        ``{"built": int, "sent": int, "errors": int, "pdf_failed": int,
           "transports": {transport: count}, "rows": [...]}``

        - ``built`` — ``build_message`` 성공한 건수
        - ``sent`` — ``email.send`` 가 ``sent=True`` 또는 transport
          ``safe-fallback`` 을 반환한 건수 (시연 측면에선 둘 다 "처리됨")
        - ``errors`` — build_message / send 실패 건수 (PDF 실패는 제외 — 첨부만 누락)
        - ``pdf_failed`` — md_to_pdf 단계 실패 건수 (T8.5 — 시연 시 PDF 실패 가시)
    """
    log = demo_logger("case03_email_quote_dispatch")
    case_dir = Path(__file__).parent
    cm = {**COLUMN_MAP, **(column_map or {})}

    if input_path is None:
        cand = case_dir / "input" / "quote_dispatch_list.xlsx"
        if not cand.exists():
            cand = Path("personas/sample_data/quote_dispatch_list.xlsx")
        input_path = cand

    if output_dir is None:
        output_dir = case_dir / "output"
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(Path(input_path))
    summary: dict[str, Any] = {
        "built": 0,
        "sent": 0,
        "errors": 0,
        "pdf_failed": 0,  # T8.5 — PDF 실패 별도 카운터 (시연 가시성)
        "transports": {},
        "rows": [],
    }
    rows_list: list[dict[str, Any]] = summary["rows"]
    transports: dict[str, int] = summary["transports"]

    if df.empty:
        log.success("입력이 비어있어 발송할 견적이 없습니다.")
        return summary

    with timer.measure(log, "견적 메일 일괄 발송", before_minutes=60):
        for _, row in df.iterrows():
            quote_no = str(row[cm["quote_no"]])
            vendor = str(row[cm["vendor"]]).strip()
            contact = str(row[cm["contact"]])
            to_addr = str(row[cm["to"]])
            # T8.5 — NaN 명시 검증. pandas read_excel은 빈 셀을 float('nan')로 채운다.
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

            # PDF 생성 (단순 견적서 1건) — 실패는 첨부만 누락하고 발송 진행.
            md_path = out_dir / f"{quote_no}.md"
            pdf_target = out_dir / f"{quote_no}.pdf"
            pdf_ok = False
            try:
                md_path.write_text(_build_quote_md(ctx), encoding="utf-8")
                pdf_mod.md_to_pdf(md_path, pdf_target)
                pdf_ok = True
            except pdf_mod.MdToPdfError as e:
                log.warning(f"[{quote_no}] pdf failed: {type(e).__name__}: {e}")
                summary["pdf_failed"] = int(summary["pdf_failed"]) + 1
            except Exception as e:  # noqa: BLE001 — pdf 단계 보호 (md write 등)
                log.warning(f"[{quote_no}] pdf step failed: {type(e).__name__}: {e}")
                summary["pdf_failed"] = int(summary["pdf_failed"]) + 1

            # 메일 빌드 + 발송 — 실패는 errors+1, 다른 row 진행.
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
                summary["built"] = int(summary["built"]) + 1

                result = email_mod.send(msg)
                # safe_mode.intercept 가 patch한 경우 dummy = {"_safe": True, ...}.
                # 정상 경로는 :class:`SendResult` (transport 키 보장).
                if isinstance(result, dict) and result.get("_safe") is True:
                    transport_name = "safe-fallback"
                    sent_flag = False
                else:
                    transport_name = str(result["transport"])
                    sent_flag = bool(result["sent"])
                if sent_flag or transport_name == "safe-fallback":
                    summary["sent"] = int(summary["sent"]) + 1
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
                summary["errors"] = int(summary["errors"]) + 1

    log.success(
        f"빌드 {summary['built']}건 / 발송 {summary['sent']}건 / "
        f"PDF 실패 {summary['pdf_failed']}건 / 에러 {summary['errors']}건"
    )
    return summary


if __name__ == "__main__":
    run()
