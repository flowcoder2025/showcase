import subprocess
import sys
from pathlib import Path

import pytest
import yaml


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
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    assert result.returncode == 0, result.stderr


def test_runner_lists_cases_with_meta_yaml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """cases/ 디렉토리에 meta.yaml이 있으면 메뉴에 노출.

    tmp_path를 cwd로 두고 runner.py를 절대경로로 호출 → 실 cases/ 오염 방지.
    """
    repo_root = Path(__file__).resolve().parent.parent
    runner_py = repo_root / "runner.py"

    cases_dir = tmp_path / "cases"
    case_dir = cases_dir / "case99_demo"
    case_dir.mkdir(parents=True)
    (case_dir / "__init__.py").write_text("")
    (case_dir / "meta.yaml").write_text(yaml.safe_dump({
        "id": "case99_demo",
        "title": "데모 케이스",
        "category": "excel",
        "external_apis": [],
    }))
    (case_dir / "scenario.py").write_text(
        "def run():\n    print('demo ran')\n"
    )

    monkeypatch.chdir(tmp_path)
    result = subprocess.run(
        [sys.executable, str(runner_py), "--list"],
        capture_output=True, text=True, cwd=tmp_path,
    )
    assert "case99_demo" in result.stdout
