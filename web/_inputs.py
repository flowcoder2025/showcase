"""Phase 3-Web T48 — per-case input form dispatch (R2-M1, R3-M3).

Each case requires a different input shape: most consume files, ``case09``
takes a single textarea, ``case10`` accepts either, and ``case06`` needs a
template plus a small form. ``render_input_form`` returns a uniform
``{"uploaded_files": [...], "config": {...}}`` payload that ``web/app.py``
forwards to ``cases.<case_id>.scenario.run(**...)``.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

CASE_INPUT_SCHEMA: dict[str, str] = {
    "case01_excel_vendor_report": "file_upload",
    "case02_excel_invoice_validation": "file_upload",
    "case03_email_quote_dispatch": "file_upload",
    "case04_discord_overdue_alert": "file_upload",
    "case05_doc_quote_generator": "file_upload",
    "case06_hwpx_govt_form_filler": "form_with_template",
    "case07_ocr_receipt_to_excel": "file_upload",
    "case08_ocr_invoice_to_csv": "file_upload",
    "case09_ai_email_drafter": "textarea",
    "case10_ai_meeting_summarizer": "file_or_textarea",
}

_FILE_TYPES_GENERIC = ["xlsx", "csv", "png", "jpg", "jpeg", "pdf"]
_FILE_TYPES_MEETING = ["txt", "md"]


def render_input_form(case_id: str) -> dict[str, Any]:
    """Render Streamlit widgets for ``case_id`` and collect the payload."""
    schema = CASE_INPUT_SCHEMA.get(case_id, "file_upload")
    result: dict[str, Any] = {"uploaded_files": [], "config": {}}

    if schema == "file_upload":
        uploaded = st.file_uploader(
            "입력 파일 업로드",
            type=_FILE_TYPES_GENERIC,
            accept_multiple_files=True,
            key=f"upload_{case_id}",
        )
        result["uploaded_files"] = list(uploaded) if uploaded else []

    elif schema == "textarea":
        message = st.text_area(
            "받은 메일 본문 (또는 응답 대상 메시지)",
            height=200,
            key=f"textarea_{case_id}",
        )
        if message:
            result["config"]["incoming_message"] = message

    elif schema == "file_or_textarea":
        choice = st.radio(
            "입력 방식",
            ["텍스트 직접 입력", "파일 업로드"],
            horizontal=True,
            key=f"choice_{case_id}",
        )
        if choice == "텍스트 직접 입력":
            text = st.text_area("회의록 본문", height=300, key=f"textarea_{case_id}")
            if text:
                result["config"]["meeting_text"] = text
        else:
            uploaded = st.file_uploader(
                "회의록 파일",
                type=_FILE_TYPES_MEETING,
                accept_multiple_files=True,
                key=f"upload_{case_id}",
            )
            result["uploaded_files"] = list(uploaded) if uploaded else []

    elif schema == "form_with_template":
        template = st.file_uploader(
            "HWPX 양식 템플릿",
            type=["hwpx"],
            key=f"template_{case_id}",
        )
        if template:
            result["uploaded_files"] = [template]
        with st.form(f"{case_id}_form"):
            project_name = st.text_input("사업명", key=f"project_{case_id}")
            applicant = st.text_input("신청자", key=f"applicant_{case_id}")
            submitted = st.form_submit_button("적용")
            if submitted:
                result["config"]["project_name"] = project_name
                result["config"]["applicant"] = applicant

    return result
