"""Tests for core.docgen.pdf — md→PDF via npx tsx skill subprocess."""

from __future__ import annotations

import subprocess
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from flowcoder_office_tools.docgen import pdf


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
    monkeypatch.setattr("flowcoder_office_tools.docgen.pdf.subprocess.run", spy)
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
    monkeypatch.setattr("flowcoder_office_tools.docgen.pdf.subprocess.run", spy)

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
    monkeypatch.setattr("flowcoder_office_tools.docgen.pdf.subprocess.run", spy)

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
    monkeypatch.setattr("flowcoder_office_tools.docgen.pdf.subprocess.run", spy)

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
    monkeypatch.setattr("flowcoder_office_tools.docgen.pdf.subprocess.run", spy)

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

    monkeypatch.setattr("flowcoder_office_tools.docgen.pdf.subprocess.run", boom)

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

    monkeypatch.setattr("flowcoder_office_tools.docgen.pdf.subprocess.run", slow)

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

    monkeypatch.setattr("flowcoder_office_tools.docgen.pdf.subprocess.run", missing)

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
    monkeypatch.setattr("flowcoder_office_tools.docgen.pdf.subprocess.run", spy)

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


# ----- T5.5 fixer additions -----


class _StderrSpy:
    """subprocess.run stub that returns nonzero stderr but exit 0, writing stub PDF."""

    def __init__(self, *, stderr: str) -> None:
        self.stderr = stderr

    def __call__(self, cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        out_path = Path(cmd[4])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"%PDF-1.4 stub\n")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="ok", stderr=self.stderr)


def test_md_to_pdf_logs_stderr_warning_on_success(
    fake_skill_dir: Path,
    md_input: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """exit 0 + stderr non-empty → demo_logger.warning 호출."""
    monkeypatch.setattr(
        "flowcoder_office_tools.docgen.pdf.subprocess.run",
        _StderrSpy(stderr="chromium download warning"),
    )
    warnings: list[str] = []

    class _StubLogger:
        def warning(self, msg: str) -> None:
            warnings.append(msg)

        def info(self, msg: str) -> None:
            pass

        def success(self, msg: str) -> None:
            pass

        def error(self, msg: str) -> None:
            pass

    monkeypatch.setattr(
        "flowcoder_office_tools.docgen.pdf.demo_logger", lambda _name: _StubLogger()
    )

    out = tmp_path / "out.pdf"
    pdf.md_to_pdf(md_input, out)

    assert len(warnings) == 1
    assert "chromium download warning" in warnings[0]
    assert "md-to-pdf stderr" in warnings[0]


def test_md_to_pdf_no_log_when_stderr_empty(
    fake_skill_dir: Path,
    md_input: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """exit 0 + stderr 비어있음 → warning 미호출."""
    monkeypatch.setattr(
        "flowcoder_office_tools.docgen.pdf.subprocess.run", _StderrSpy(stderr="   ")
    )
    warnings: list[str] = []

    class _StubLogger:
        def warning(self, msg: str) -> None:
            warnings.append(msg)

        def info(self, msg: str) -> None:
            pass

        def success(self, msg: str) -> None:
            pass

        def error(self, msg: str) -> None:
            pass

    monkeypatch.setattr(
        "flowcoder_office_tools.docgen.pdf.demo_logger", lambda _name: _StubLogger()
    )

    out = tmp_path / "out.pdf"
    pdf.md_to_pdf(md_input, out)

    assert warnings == []


def test_md_to_pdf_stderr_truncated_to_500_chars(
    fake_skill_dir: Path,
    md_input: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """긴 stderr는 500자로 컷."""
    long = "x" * 1000
    monkeypatch.setattr("flowcoder_office_tools.docgen.pdf.subprocess.run", _StderrSpy(stderr=long))
    warnings: list[str] = []

    class _StubLogger:
        def warning(self, msg: str) -> None:
            warnings.append(msg)

        def info(self, msg: str) -> None:
            pass

        def success(self, msg: str) -> None:
            pass

        def error(self, msg: str) -> None:
            pass

    monkeypatch.setattr(
        "flowcoder_office_tools.docgen.pdf.demo_logger", lambda _name: _StubLogger()
    )

    out = tmp_path / "out.pdf"
    pdf.md_to_pdf(md_input, out)
    # warning prefix "md-to-pdf stderr: " + 500 chars max
    assert len(warnings) == 1
    # extract part after prefix
    body = warnings[0].split("md-to-pdf stderr: ", 1)[1]
    assert len(body) <= 500


def test_md_to_pdf_invalid_style_raises_value_error(
    fake_skill_dir: Path,
    md_input: Path,
    tmp_path: Path,
) -> None:
    """style 런타임 validation: 잘못된 값 → ValueError."""
    out = tmp_path / "out.pdf"
    with pytest.raises(ValueError, match="unknown style") as exc:
        pdf.md_to_pdf(md_input, out, style="invalid")  # type: ignore[arg-type]
    msg = str(exc.value)
    assert "invalid" in msg
    # Valid list mentioned
    for s in ("document", "report", "minimal"):
        assert s in msg


@pytest.mark.parametrize("valid_style", ["document", "report", "minimal"])
def test_md_to_pdf_valid_styles_pass(
    fake_skill_dir: Path,
    md_input: Path,
    tmp_path: Path,
    run_spy: _RunSpy,
    valid_style: str,
) -> None:
    """3가지 유효 style 모두 정상 통과."""
    out = tmp_path / f"out_{valid_style}.pdf"
    pdf.md_to_pdf(md_input, out, style=valid_style)  # type: ignore[arg-type]
    cmd = run_spy.calls[-1]["cmd"]
    assert cmd[cmd.index("--style") + 1] == valid_style
