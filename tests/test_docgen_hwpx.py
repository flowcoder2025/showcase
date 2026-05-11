"""Tests for core.docgen.hwpx — HWPX 양식 자동 채우기 wrapper.

Fixture: ``personas/sample_data/forms/test_template.hwpx`` (Skeleton.hwpx
derivative, MIT). 테이블 id=``999000001``, 3 rows × 2 cols, 사전 채워진 텍스트:
- (0,0): 항목, (1,0): 값
- (0,1): 신청자명, (1,1): □ 미정
- (0,2): 사업명, (1,2): (빈 셀)
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from flowcoder_office_tools.docgen import hwpx

FIXTURE = Path(__file__).parent.parent / "personas" / "sample_data" / "forms" / "test_template.hwpx"
FIXTURE_TABLE_ID = "999000001"


@pytest.fixture
def template(tmp_path: Path) -> Path:
    """tmp_path에 test_template.hwpx 사본 — 원본 보호."""
    if not FIXTURE.exists():
        pytest.skip(f"test fixture missing: {FIXTURE}")
    dst = tmp_path / "in.hwpx"
    shutil.copyfile(FIXTURE, dst)
    return dst


# ── fill_form: happy path ─────────────────────────────────────────────


def test_fill_form_python_pattern(template: Path, tmp_path: Path) -> None:
    """cell_fills가 출력 HWPX에 반영되어 extract_text로 다시 보임."""
    out = tmp_path / "out.hwpx"
    hwpx.fill_form(
        template_path=template,
        out_path=out,
        cell_fills=[
            {"table_id": FIXTURE_TABLE_ID, "col": 1, "row": 2, "text": "AX상사 신사업"},
        ],
    )
    assert out.exists()
    text = hwpx.extract_text(out)
    assert "AX상사 신사업" in text
    # 기존 라벨도 그대로 보존
    assert "신청자명" in text
    assert "사업명" in text


def test_fill_form_checkbox_toggle(template: Path, tmp_path: Path) -> None:
    """text_replacements로 체크박스 토글 (``□ 미정`` → ``☑ 확정``)."""
    out = tmp_path / "out.hwpx"
    hwpx.fill_form(
        template_path=template,
        out_path=out,
        text_replacements=[
            {
                "table_id": FIXTURE_TABLE_ID,
                "col": 1,
                "row": 1,
                "old": "□ 미정",
                "new": "☑ 확정",
            },
        ],
    )
    text = hwpx.extract_text(out)
    assert "☑ 확정" in text
    assert "□ 미정" not in text


def test_fill_form_combined(template: Path, tmp_path: Path) -> None:
    """cell_fills + text_replacements 동시 적용."""
    out = tmp_path / "out.hwpx"
    hwpx.fill_form(
        template_path=template,
        out_path=out,
        cell_fills=[
            {"table_id": FIXTURE_TABLE_ID, "col": 1, "row": 2, "text": "사업 ABC"},
        ],
        text_replacements=[
            {
                "table_id": FIXTURE_TABLE_ID,
                "col": 1,
                "row": 1,
                "old": "□ 미정",
                "new": "☑ 확정",
            },
        ],
    )
    text = hwpx.extract_text(out)
    assert "사업 ABC" in text
    assert "☑ 확정" in text


def test_fill_form_empty_cells_copies_template(template: Path, tmp_path: Path) -> None:
    """cell_fills/text_replacements 둘 다 None이어도 출력 파일 생성 + 원본 텍스트 보존."""
    out = tmp_path / "out.hwpx"
    original_text = hwpx.extract_text(template)
    hwpx.fill_form(template_path=template, out_path=out)
    assert out.exists()
    out_text = hwpx.extract_text(out)
    # 모든 라벨/값이 그대로 살아있어야 함
    for marker in ("항목", "신청자명", "□ 미정", "사업명"):
        assert marker in original_text
        assert marker in out_text


def test_fill_form_empty_lists_also_pass_through(template: Path, tmp_path: Path) -> None:
    """빈 리스트도 None과 동일하게 처리되어야 함."""
    out = tmp_path / "out.hwpx"
    hwpx.fill_form(
        template_path=template,
        out_path=out,
        cell_fills=[],
        text_replacements=[],
    )
    assert out.exists()
    text = hwpx.extract_text(out)
    assert "신청자명" in text


def test_fill_form_creates_parent_directory(template: Path, tmp_path: Path) -> None:
    """out_path의 부모 디렉토리가 없으면 자동 생성."""
    out = tmp_path / "nested" / "deep" / "out.hwpx"
    hwpx.fill_form(template_path=template, out_path=out)
    assert out.exists()


# ── fill_form: error paths ────────────────────────────────────────────


def test_fill_form_missing_template_raises(tmp_path: Path) -> None:
    """존재하지 않는 template은 FileNotFoundError."""
    missing = tmp_path / "does-not-exist.hwpx"
    out = tmp_path / "out.hwpx"
    with pytest.raises(FileNotFoundError, match="HWPX template not found"):
        hwpx.fill_form(template_path=missing, out_path=out)


def test_fill_form_corrupt_template_raises_value_error(tmp_path: Path) -> None:
    """ZIP이 아닌 바이트 파일을 template으로 주면 ValueError (BadZipFile wrap)."""
    bogus = tmp_path / "bogus.hwpx"
    bogus.write_bytes(b"this is not a zip")
    out = tmp_path / "out.hwpx"
    with pytest.raises(ValueError, match="corrupt HWPX template"):
        hwpx.fill_form(template_path=bogus, out_path=out)


def test_fill_form_unknown_table_id_does_not_raise(template: Path, tmp_path: Path) -> None:
    """모르는 table_id는 HwpxEditor가 stderr에 경고만 찍고 set_cell이 False 반환.

    본 wrapper는 그대로 통과시키며 출력 파일은 정상 생성된다 (operator는 결과
    파일을 한글에서 열어 누락 여부를 확인). 이 동작을 명시적으로 고정한다.
    """
    out = tmp_path / "out.hwpx"
    hwpx.fill_form(
        template_path=template,
        out_path=out,
        cell_fills=[
            {"table_id": "0000000000", "col": 1, "row": 2, "text": "ignored"},
        ],
    )
    assert out.exists()
    text = hwpx.extract_text(out)
    # 채우려던 텍스트는 들어가지 않음, 원본은 그대로
    assert "ignored" not in text
    assert "신청자명" in text


# ── extract_text ──────────────────────────────────────────────────────


def test_extract_text_returns_non_empty(template: Path) -> None:
    text = hwpx.extract_text(template)
    assert isinstance(text, str)
    assert len(text) > 0
    # 시드 텍스트 일부가 반드시 포함
    assert "신청자명" in text


def test_extract_text_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="HWPX file not found"):
        hwpx.extract_text(tmp_path / "missing.hwpx")


def test_extract_text_non_zip_raises_value_error(tmp_path: Path) -> None:
    bogus = tmp_path / "bogus.hwpx"
    bogus.write_bytes(b"not a zip at all")
    with pytest.raises(ValueError, match="not a valid HWPX"):
        hwpx.extract_text(bogus)


# ── env override ──────────────────────────────────────────────────────


def test_env_override_dir_used_on_import(monkeypatch: pytest.MonkeyPatch) -> None:
    """``AX_HWPX_EDITOR_DIR``가 잘못된 경로면 _import_hwpx_editor가 ImportError.

    이전 테스트에서 실제 스킬 dir이 ``sys.path``에 추가되어 있을 수 있으므로
    실제 dir과 ``hwpx_utils`` 캐시 양쪽을 제거하고, ``_HWPX_SKILL_DIR``을
    존재하지 않는 경로로 monkeypatch한다.
    """
    import sys as _sys

    real_dir = hwpx._HWPX_SKILL_DIR
    new_path = [p for p in _sys.path if p != real_dir]
    monkeypatch.setattr(_sys, "path", new_path)
    monkeypatch.delitem(_sys.modules, "hwpx_utils", raising=False)
    monkeypatch.setattr(hwpx, "_HWPX_SKILL_DIR", "/nonexistent/path/to/hwpx-editor")

    with pytest.raises(ImportError):
        hwpx._import_hwpx_editor()
