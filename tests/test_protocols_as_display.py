"""T35 — `cases._protocols.as_display` Streamlit 화면 sanitize 보장 (R1-C1).

`as_display`는 `serialize_result`와 동일한 sanitize를 적용하는 단일 진입점.
raw `result`를 st.* 위젯에 직접 넘기는 패턴을 차단하기 위한 함수.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cases._protocols import ScenarioResult, as_display


def _empty_result(case_id: str = "x") -> ScenarioResult:
    return {
        "case_id": case_id,
        "summary_text": "ok",
        "output_files": [],
        "metrics": {},
        "failures": [],
        "extras": {},
    }


def test_as_display_masks_failures() -> None:
    sentinel = "ya29.SCREEN_LEAK_TEST"
    result = _empty_result("case03")
    result["failures"] = [{"vendor": "v1", "error": f"401 token={sentinel}"}]
    display = as_display(result)
    assert "SCREEN_LEAK_TEST" not in str(display)


def test_as_display_returns_dict() -> None:
    """st.* 위젯에 넘길 dict 형태."""
    result = _empty_result()
    display = as_display(result)
    assert isinstance(display, dict)


def test_as_display_returns_full_keys() -> None:
    """6 ScenarioResult 필드 모두 dict에 존재."""
    result = _empty_result()
    display = as_display(result)
    assert set(display.keys()) == {
        "case_id",
        "summary_text",
        "output_files",
        "metrics",
        "failures",
        "extras",
    }


def test_as_display_masks_summary_text() -> None:
    sentinel = "sk-or-v1-DISPLAY_SUMMARY_LEAK"
    result = _empty_result()
    result["summary_text"] = f"failure: {sentinel}"
    display = as_display(result)
    assert "DISPLAY_SUMMARY_LEAK" not in str(display)


def test_as_display_masks_extras_dataclass() -> None:
    """R1-L3 + R1-C1: dataclass도 화면 노출 시 sanitize 거침."""

    @dataclass
    class Note:
        body: str

    sentinel = "ghp_DISPLAY_DATACLASS_LEAK_1234567890"
    result = _empty_result("case10")
    result["extras"] = {"note": Note(body=f"see {sentinel}")}
    display = as_display(result)
    assert "DISPLAY_DATACLASS_LEAK" not in str(display)


def test_as_display_masks_output_files_path(tmp_path: Path) -> None:
    """output_files path도 sanitize 거침 (R3-M3 + R1-C1)."""
    sentinel = "sk-or-v1-DISPLAY_PATH_LEAK_KEY"
    sus_path = tmp_path / f"out-{sentinel}.txt"
    sus_path.write_bytes(b"")
    result = _empty_result()
    result["output_files"] = [sus_path]
    display = as_display(result)
    assert "DISPLAY_PATH_LEAK_KEY" not in str(display)
