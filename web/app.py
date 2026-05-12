"""Phase 3-Web T47 — Streamlit MVP entry point.

Local-only demo surface for the in-house consulting flow. Bound to 127.0.0.1
via ``.streamlit/config.toml`` + the assertion at module load — both layers
must succeed for external exposure to be possible.

T48 will wire per-case input forms; this module only renders the case grid
and the safe-mode toggle.
"""

from __future__ import annotations

import os

import streamlit as st

_ADDR = os.environ.get("STREAMLIT_SERVER_ADDRESS", "127.0.0.1")
assert _ADDR in {"127.0.0.1", "localhost"}, f"외부 노출 금지: STREAMLIT_SERVER_ADDRESS={_ADDR!r}"


CASES: list[tuple[str, str]] = [
    ("case01_excel_vendor_report", "거래처 월별 매출 보고서"),
    ("case02_excel_invoice_validation", "단가 검증 + Discord 이상치 알림"),
    ("case03_email_quote_dispatch", "견적 메일 일괄 발송"),
    ("case04_discord_overdue_alert", "미수금 단계별 Discord 알림"),
    ("case05_doc_quote_generator", "견적서/거래명세서 (Word + PDF)"),
    ("case06_hwpx_govt_form_filler", "정부지원사업 HWPX 양식"),
    ("case07_ocr_receipt_to_excel", "영수증 OCR → 경비 정리"),
    ("case08_ocr_invoice_to_csv", "세금계산서 OCR → 회계 CSV"),
    ("case09_ai_email_drafter", "AI 메일 초안 (3안)"),
    ("case10_ai_meeting_summarizer", "회의록 요약 + 액션아이템"),
]


def main() -> None:
    st.set_page_config(page_title="AX Showcase", layout="wide")
    st.title("AX Showcase — 사무자동화 시연")

    with st.sidebar:
        st.subheader("실행 모드")
        running = bool(st.session_state.get("running", False))
        safe_mode = st.toggle(
            "Safe mode (외부 호출 차단)",
            value=bool(st.session_state.get("safe_mode", False)),
            disabled=running,
            help="외부 API 호출 없이 캐시·더미 응답으로 실행. 실행 중에는 변경 불가.",
        )
        st.session_state["safe_mode"] = safe_mode

    st.subheader("케이스 선택")
    cols = st.columns(2)
    for idx, (case_id, title) in enumerate(CASES):
        col = cols[idx % 2]
        clicked = col.button(
            f"**{title}**\n`{case_id}`",
            use_container_width=True,
            key=f"case_btn_{case_id}",
        )
        if clicked:
            st.session_state["selected_case"] = case_id

    selected = st.session_state.get("selected_case")
    if selected:
        st.divider()
        st.subheader(f"실행: {selected}")
        st.caption("입력 form + 실행 wiring 은 T48 에서 구현됩니다.")


if __name__ == "__main__":
    main()
