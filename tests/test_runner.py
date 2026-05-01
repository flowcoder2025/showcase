import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

import runner as runner_mod


def test_runner_check_exits_zero_on_clean_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--check`는 의존성·키 누락 시 exit 1, 모두 OK 시 0."""
    # 최소 환경 구성: env 키 모두 더미
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/x/y")
    monkeypatch.setenv("DEMO_SAFE", "1")  # 외부 호출 회피

    # check만 실행 — 실제 케이스 발견 없이 동작해야
    result = subprocess.run(
        [sys.executable, "runner.py", "--check"],
        capture_output=True,
        text=True,
        env={**__import__("os").environ},
    )
    assert result.returncode == 0, result.stderr


def test_runner_lists_cases_with_meta_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """cases/ 디렉토리에 meta.yaml이 있으면 메뉴에 노출.

    tmp_path를 cwd로 두고 runner.py를 절대경로로 호출 → 실 cases/ 오염 방지.
    """
    repo_root = Path(__file__).resolve().parent.parent
    runner_py = repo_root / "runner.py"

    cases_dir = tmp_path / "cases"
    case_dir = cases_dir / "case99_demo"
    case_dir.mkdir(parents=True)
    (case_dir / "__init__.py").write_text("")
    (case_dir / "meta.yaml").write_text(
        yaml.safe_dump(
            {
                "id": "case99_demo",
                "title": "데모 케이스",
                "category": "excel",
                "external_apis": [],
            }
        )
    )
    (case_dir / "scenario.py").write_text("def run():\n    print('demo ran')\n")

    monkeypatch.chdir(tmp_path)
    result = subprocess.run(
        [sys.executable, str(runner_py), "--list"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert "case99_demo" in result.stdout


# ----- T5.5 fixer additions: --check --strict md-to-pdf skill validation -----


class _CapLogger:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.infos: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def info(self, msg: str) -> None:
        self.infos.append(msg)

    def success(self, msg: str) -> None:
        self.infos.append(msg)


def test_check_strict_md_to_pdf_skill_missing_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AX_MD_TO_PDF_DIR이 존재하지 않으면 strict check 실패."""
    bogus = tmp_path / "nonexistent_skill_dir"
    monkeypatch.setenv("AX_MD_TO_PDF_DIR", str(bogus))

    log = _CapLogger()
    ok = runner_mod._check_md_to_pdf_skill(log)
    assert ok is False
    assert any("md-to-pdf skill dir not found" in e for e in log.errors)


def test_check_strict_md_to_pdf_skill_present_passes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """skill dir 존재 + npx 호출 성공 → strict check 통과."""
    sk = tmp_path / "fake_skill"
    sk.mkdir()
    monkeypatch.setenv("AX_MD_TO_PDF_DIR", str(sk))

    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert cmd[0] == "npx"
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="10.0.0\n", stderr="")

    monkeypatch.setattr("runner.subprocess.run", fake_run)

    log = _CapLogger()
    ok = runner_mod._check_md_to_pdf_skill(log)
    assert ok is True
    assert log.errors == []


# ----- T8.5 fixer additions: --check --strict GMAIL_SENDER validation -----


def test_check_strict_gmail_sender_missing_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T8.5 — email transport(SMTP) 설정은 있지만 ``GMAIL_SENDER`` 미설정 시 strict 실패.

    case03 ``build_message``는 ``GMAIL_SENDER`` 없으면 빌드 시점에 실패하므로
    strict check에서 사전 차단해야 시연 직전 발견을 막는다.
    """
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "ax-sales@example.com")
    monkeypatch.delenv("GMAIL_SENDER", raising=False)
    monkeypatch.delenv("GMAIL_OAUTH_CREDENTIALS", raising=False)

    log = _CapLogger()
    ok = runner_mod._check_email_transport(log)
    assert ok is False
    assert any("GMAIL_SENDER" in e for e in log.errors), log.errors


def test_check_strict_gmail_sender_present_passes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T8.5 — SMTP credential + GMAIL_SENDER 모두 있으면 통과."""
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "ax-sales@example.com")
    monkeypatch.setenv("GMAIL_SENDER", "AX Sales <ax-sales@example.com>")
    monkeypatch.delenv("GMAIL_OAUTH_CREDENTIALS", raising=False)

    log = _CapLogger()
    ok = runner_mod._check_email_transport(log)
    assert ok is True
    assert log.errors == []


def test_check_strict_gmail_sender_with_gmail_oauth_passes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T8.5 — Gmail OAuth credential + GMAIL_SENDER 모두 있으면 통과."""
    creds = tmp_path / "credentials.json"
    creds.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("GMAIL_OAUTH_CREDENTIALS", str(creds))
    monkeypatch.setenv("GMAIL_SENDER", "AX Sales <ax-sales@example.com>")
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)

    log = _CapLogger()
    ok = runner_mod._check_email_transport(log)
    assert ok is True


def test_check_strict_md_to_pdf_skill_npx_missing_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """skill dir은 있지만 npx가 PATH에 없으면 strict check 실패."""
    sk = tmp_path / "fake_skill"
    sk.mkdir()
    monkeypatch.setenv("AX_MD_TO_PDF_DIR", str(sk))

    def missing(cmd: list[str], **kwargs: Any) -> Any:
        raise FileNotFoundError("npx not in PATH")

    monkeypatch.setattr("runner.subprocess.run", missing)

    log = _CapLogger()
    ok = runner_mod._check_md_to_pdf_skill(log)
    assert ok is False
    assert any("npx not available" in e for e in log.errors)
