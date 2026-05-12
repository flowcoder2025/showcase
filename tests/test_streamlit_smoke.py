"""Phase 3-Web T50 — Streamlit launcher smoke + ``as_display`` leak guard.

Five tests close out Phase 3-Web by exercising the seams that have no other
coverage:

* ``test_app_imports`` — the ``streamlit run`` entry point must import without
  side effects.
* ``test_create_run_dir_isolated`` — every invocation gets a fresh writable
  surface (R1-C2 path traversal precondition).
* ``test_render_result_sanitizes_failures_with_sentinel`` — R1-C1 plan
  prescription: a Gmail-token sentinel embedded in a ``failures`` entry must
  *not* survive ``render_result`` and reach any ``st.*`` widget.
* ``test_execute_case_safe_mode`` — end-to-end execute_case in safe mode
  produces a ``run.json`` (single-page round-trip without external APIs).
* ``test_case_input_schema_covers_all_cases`` — every published case has an
  input form (R2-M1 — no silent gaps in the menu).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest


def test_app_imports() -> None:
    import web.app

    assert callable(web.app.main)


def test_create_run_dir_isolated(tmp_path: Path) -> None:
    from web._runs import create_run_dir

    run_dir = create_run_dir(tmp_path / "runs")
    assert (run_dir / "input").is_dir()
    assert (run_dir / "output").is_dir()
    assert run_dir.parent == tmp_path / "runs"


def test_render_result_sanitizes_failures_with_sentinel() -> None:
    """R1-C1 plan 처방: render 경로에서 sentinel 토큰 leak 0건."""
    from web._render import render_result

    sentinel = "ya29.STREAMLIT_RENDER_LEAK_TEST"
    fake_result: dict[str, Any] = {
        "run_id": "test",
        "run_dir": Path("/tmp/test"),
        "result": {
            "case_id": "case03",
            "summary_text": "ok",
            "output_files": [],
            "metrics": {},
            "failures": [{"vendor": "v1", "error": f"401 token={sentinel}"}],
            "extras": {},
        },
    }

    rendered_text: list[str] = []

    def capture(x: Any, **_: Any) -> None:
        rendered_text.append(str(x))

    with patch("web._render.st") as mock_st:
        mock_st.success.side_effect = capture
        mock_st.warning.side_effect = capture
        mock_st.dataframe.side_effect = capture
        mock_st.json.side_effect = capture
        mock_st.caption.side_effect = capture
        mock_st.subheader.side_effect = lambda *_a, **_kw: None
        mock_st.download_button.side_effect = lambda **_kw: None
        # st.expander is used as a context manager — mock returns a MagicMock
        # whose __enter__/__exit__ are auto-wired by unittest.mock.
        render_result(fake_result)

    combined = " ".join(rendered_text)
    assert sentinel not in combined, f"sentinel leak in render: {combined[:200]}"
    # Positive sanity: the masked form is present (proves we exercised the path).
    assert "ya29.***" in combined


def test_execute_case_safe_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Safe-mode round trip: run.json materializes, no external API hit.

    Uses ``case09_ai_email_drafter`` instead of the spec's ``case01`` because
    case01 falls back to ``personas/sample_data/vendors/`` which is generated
    on demand and not part of the smoke test contract. case09 takes its full
    input via ``config["incoming_message"]`` so the run is fully hermetic.
    """
    monkeypatch.setattr("web.app.RUNS_ROOT", tmp_path / "runs")
    from web.app import execute_case

    result = execute_case(
        case_id="case09_ai_email_drafter",
        form_result={
            "uploaded_files": [],
            "config": {"incoming_message": "제목: 단가 문의\n본문: 안녕하세요."},
        },
        safe_mode=True,
    )

    assert result["run_id"]
    assert (result["run_dir"] / "run.json").is_file()
    assert result["result"]["case_id"] == "case09"


def test_case_input_schema_covers_all_cases() -> None:
    """R2-M1: 10 케이스가 모두 입력 스키마를 갖는다 (메뉴 카드 ↔ 폼 1:1)."""
    from web._inputs import CASE_INPUT_SCHEMA

    expected = {
        "case01_excel_vendor_report",
        "case02_excel_invoice_validation",
        "case03_email_quote_dispatch",
        "case04_discord_overdue_alert",
        "case05_doc_quote_generator",
        "case06_hwpx_govt_form_filler",
        "case07_ocr_receipt_to_excel",
        "case08_ocr_invoice_to_csv",
        "case09_ai_email_drafter",
        "case10_ai_meeting_summarizer",
    }
    assert set(CASE_INPUT_SCHEMA.keys()) == expected
