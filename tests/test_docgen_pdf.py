"""Tests for core.docgen.pdf — md→PDF via npx tsx skill subprocess."""

from __future__ import annotations

import subprocess
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from core.docgen import pdf


@pytest.fixture
def fake_skill_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a fake md-to-pdf skill dir and override env var."""
    sk = tmp_path / "fake_skill"
    sk.mkdir()
    monkeypatch.setenv("AX_MD_TO_PDF_DIR", str(sk))
    return sk


@pytest.fixture
def md_input(tmp_path: Path) -> Path:
    p = tmp_path / "in.md"
    p.write_text("# Hello\n\nWorld.\n", encoding="utf-8")
    return p


class _RunSpy:
    """Captures subprocess.run kwargs and writes a stub PDF to out_path."""

    def __init__(self, *, write_output: bool = True) -> None:
        self.calls: list[dict[str, Any]] = []
        self.write_output = write_output

    def __call__(self, cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append({"cmd": cmd, **kwargs})
        if self.write_output:
            # cmd: [npx, tsx, <script>, <md>, <out>, --style, <style>]
            out_path = Path(cmd[4])
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(b"%PDF-1.4 stub\n")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="ok", stderr="")


@pytest.fixture
def run_spy(monkeypatch: pytest.MonkeyPatch) -> Generator[_RunSpy, None, None]:
    spy = _RunSpy()
    monkeypatch.setattr("core.docgen.pdf.subprocess.run", spy)
    yield spy


def test_md_to_pdf_calls_npx_tsx_with_correct_args(
    fake_skill_dir: Path,
    md_input: Path,
    tmp_path: Path,
    run_spy: _RunSpy,
) -> None:
    out = tmp_path / "out.pdf"
    pdf.md_to_pdf(md_input, out)

    assert len(run_spy.calls) == 1
    call = run_spy.calls[0]
    cmd = call["cmd"]
    assert cmd[0:3] == ["npx", "tsx", "scripts/md-to-pdf.ts"]
    assert "--style" in cmd
    assert cmd[cmd.index("--style") + 1] == "document"
    assert call["cwd"] == str(fake_skill_dir)
    assert call["timeout"] == 60
    assert call["check"] is True
    assert call["capture_output"] is True
    assert call["text"] is True


def test_md_to_pdf_passes_style_argument(
    fake_skill_dir: Path,
    md_input: Path,
    tmp_path: Path,
    run_spy: _RunSpy,
) -> None:
    out = tmp_path / "out.pdf"
    pdf.md_to_pdf(md_input, out, style="report")

    cmd = run_spy.calls[0]["cmd"]
    assert "--style" in cmd
    assert cmd[cmd.index("--style") + 1] == "report"


def test_md_to_pdf_env_override_dir(
    tmp_path: Path,
    md_input: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sk = tmp_path / "custom_skill"
    sk.mkdir()
    monkeypatch.setenv("AX_MD_TO_PDF_DIR", str(sk))

    spy = _RunSpy()
    monkeypatch.setattr("core.docgen.pdf.subprocess.run", spy)

    out = tmp_path / "out.pdf"
    pdf.md_to_pdf(md_input, out)
    assert spy.calls[0]["cwd"] == str(sk)


def test_md_to_pdf_env_override_script(
    fake_skill_dir: Path,
    md_input: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AX_MD_TO_PDF_SCRIPT", "custom/path.ts")
    spy = _RunSpy()
    monkeypatch.setattr("core.docgen.pdf.subprocess.run", spy)

    out = tmp_path / "out.pdf"
    pdf.md_to_pdf(md_input, out)
    assert spy.calls[0]["cmd"][2] == "custom/path.ts"


def test_md_to_pdf_env_override_timeout(
    fake_skill_dir: Path,
    md_input: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AX_MD_TO_PDF_TIMEOUT", "120")
    spy = _RunSpy()
    monkeypatch.setattr("core.docgen.pdf.subprocess.run", spy)

    out = tmp_path / "out.pdf"
    pdf.md_to_pdf(md_input, out)
    assert spy.calls[0]["timeout"] == 120


def test_md_to_pdf_explicit_timeout_overrides_env(
    fake_skill_dir: Path,
    md_input: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AX_MD_TO_PDF_TIMEOUT", "120")
    spy = _RunSpy()
    monkeypatch.setattr("core.docgen.pdf.subprocess.run", spy)

    out = tmp_path / "out.pdf"
    pdf.md_to_pdf(md_input, out, timeout=30)
    assert spy.calls[0]["timeout"] == 30


def test_md_to_pdf_missing_input_raises(
    fake_skill_dir: Path,
    tmp_path: Path,
) -> None:
    out = tmp_path / "out.pdf"
    with pytest.raises(FileNotFoundError, match="md input not found"):
        pdf.md_to_pdf(tmp_path / "missing.md", out)


def test_md_to_pdf_missing_skill_dir_raises(
    md_input: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bogus = tmp_path / "nonexistent"
    monkeypatch.setenv("AX_MD_TO_PDF_DIR", str(bogus))

    out = tmp_path / "out.pdf"
    with pytest.raises(FileNotFoundError, match="md-to-pdf skill dir not found") as exc:
        pdf.md_to_pdf(md_input, out)
    assert str(bogus) in str(exc.value)


def test_md_to_pdf_subprocess_failure_raises_mdtopdferror(
    fake_skill_dir: Path,
    md_input: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(cmd: list[str], **kwargs: Any) -> Any:
        raise subprocess.CalledProcessError(
            returncode=1, cmd=cmd, output="some out", stderr="boom-stderr"
        )

    monkeypatch.setattr("core.docgen.pdf.subprocess.run", boom)

    out = tmp_path / "out.pdf"
    with pytest.raises(pdf.MdToPdfError, match="md-to-pdf failed") as exc:
        pdf.md_to_pdf(md_input, out)
    assert "boom-stderr" in str(exc.value)
    assert "exit 1" in str(exc.value)


def test_md_to_pdf_timeout_raises_mdtopdferror(
    fake_skill_dir: Path,
    md_input: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def slow(cmd: list[str], **kwargs: Any) -> Any:
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=60)

    monkeypatch.setattr("core.docgen.pdf.subprocess.run", slow)

    out = tmp_path / "out.pdf"
    with pytest.raises(pdf.MdToPdfError, match="timeout"):
        pdf.md_to_pdf(md_input, out)


def test_md_to_pdf_npx_not_found_raises_mdtopdferror(
    fake_skill_dir: Path,
    md_input: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing(cmd: list[str], **kwargs: Any) -> Any:
        raise FileNotFoundError("npx not in PATH")

    monkeypatch.setattr("core.docgen.pdf.subprocess.run", missing)

    out = tmp_path / "out.pdf"
    with pytest.raises(pdf.MdToPdfError, match="npx/tsx not found"):
        pdf.md_to_pdf(md_input, out)


def test_md_to_pdf_zero_exit_but_no_output_raises(
    fake_skill_dir: Path,
    md_input: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = _RunSpy(write_output=False)
    monkeypatch.setattr("core.docgen.pdf.subprocess.run", spy)

    out = tmp_path / "out.pdf"
    with pytest.raises(pdf.MdToPdfError, match="output file missing"):
        pdf.md_to_pdf(md_input, out)


def test_md_to_pdf_creates_output_parent_dir(
    fake_skill_dir: Path,
    md_input: Path,
    tmp_path: Path,
    run_spy: _RunSpy,
) -> None:
    out = tmp_path / "nested" / "deeper" / "out.pdf"
    assert not out.parent.exists()
    pdf.md_to_pdf(md_input, out)
    assert out.parent.exists()
    assert out.exists()


def test_md_to_pdf_default_style_is_document(
    fake_skill_dir: Path,
    md_input: Path,
    tmp_path: Path,
    run_spy: _RunSpy,
) -> None:
    out = tmp_path / "out.pdf"
    pdf.md_to_pdf(md_input, out)
    cmd = run_spy.calls[0]["cmd"]
    assert cmd[cmd.index("--style") + 1] == "document"
