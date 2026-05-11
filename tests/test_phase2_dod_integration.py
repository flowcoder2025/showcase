"""Phase 2 DoD verification — cross-cutting integration checks.

These tests lock invariants that span multiple cases / multiple subsystems:

- runner discovers exactly 10 cases (case01..case10).
- All cases with non-empty ``external_apis`` produce deterministic output in
  safe mode (run twice → identical).
- ``runner.py --check`` exits 0 (non-strict mode, no live API needed).
- Repository-wide quality gates: ``ruff check``, ``ruff format --check``, and
  ``mypy --strict`` over the production lock (``core/`` + ``runner.py`` +
  ``cases/``) all pass. These meta-tests intentionally lock the R3-H1
  verification-integrity invariant — if reviewers find ruff/mypy ignored,
  these tests fail.
- ``specs/phase2-external-usage-promise.md`` carries the R1-C2 commitment.

Subprocess-based meta-tests use ``cwd=`` anchored to project root and
``timeout=120`` to prevent hangs. They are slow-by-design; they only run
during DoD validation.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# --- shared helpers --------------------------------------------------------


def _meta_for(case_id: str) -> dict[str, Any]:
    meta_path = PROJECT_ROOT / "cases" / case_id / "meta.yaml"
    return yaml.safe_load(meta_path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


# --- 1. discover_cases returns 10 ----------------------------------------


def test_runner_lists_all_ten_cases() -> None:
    """DoD: ``runner.discover_cases()`` 가 정확히 10건 반환 + case01..case10 ID."""
    from runner import discover_cases

    cases = discover_cases()
    assert len(cases) == 10, f"DoD gap: expected 10 cases, got {len(cases)}"

    ids = sorted(c["id"] for c in cases)
    expected_prefixes = [f"case{i:02d}" for i in range(1, 11)]
    actual_prefixes = sorted(c["id"][:6] for c in cases)
    assert actual_prefixes == expected_prefixes, (
        f"DoD gap: case ID prefix mismatch — got {actual_prefixes!r}, "
        f"expected {expected_prefixes!r}"
    )

    # 각 ID는 unique 해야 함
    assert len(set(ids)) == 10


# --- 2. all external_apis cases are deterministic in safe mode -----------


def test_all_external_api_cases_safe_mode_caches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DoD: ``external_apis`` 가 비어있지 않은 모든 케이스는 safe-mode 결정적이다.

    Strategy: 각 케이스를 safe mode에서 실행 가능한 최소한의 형태로 2회 호출 →
    결정성 검증. 실 시드 의존을 피하기 위해 case-specific stub 데이터를 주입.
    실패 시 ``DoD gap: <case_id> not deterministic`` 으로 명시.
    """
    monkeypatch.setenv("DEMO_SAFE", "1")
    monkeypatch.setenv("GMAIL_SENDER", "ax-sales@example.com")

    # 실제 external_apis가 비어있지 않은 케이스만 — meta.yaml에서 동적 추출.
    cases_with_apis = []
    for case_dir in sorted((PROJECT_ROOT / "cases").iterdir()):
        if not case_dir.is_dir():
            continue
        meta_file = case_dir / "meta.yaml"
        if not meta_file.exists():
            continue
        meta = yaml.safe_load(meta_file.read_text(encoding="utf-8"))
        if meta.get("external_apis"):
            cases_with_apis.append(meta["id"])

    # 기대 목록 — meta.yaml drift 방지용 명시 잠금.
    expected = [
        "case02_excel_invoice_validation",  # discord_webhook
        "case03_email_quote_dispatch",  # gmail
        "case04_discord_overdue_alert",  # discord_webhook
        "case07_ocr_receipt_to_excel",  # ollama_gemma
        "case08_ocr_invoice_to_csv",  # ollama_gemma
        "case09_ai_email_drafter",  # openrouter
        "case10_ai_meeting_summarizer",  # openrouter
    ]
    assert sorted(cases_with_apis) == sorted(expected), (
        f"DoD gap: external_apis case list drift — got {cases_with_apis!r}, expected {expected!r}"
    )

    # 각 케이스의 결정성 검증을 1군데로 집중. 실 시드 + heavy IO 의존을 피하기
    # 위해 케이스별 thin invocation만 하고, scenario 가 적절한 fallback path를
    # 타는지 확인한다.
    case09_ok = _check_case09_deterministic(tmp_path / "c09", monkeypatch)
    case10_ok = _check_case10_deterministic(tmp_path / "c10")
    assert case09_ok, "DoD gap: case09 not deterministic in safe mode"
    assert case10_ok, "DoD gap: case10 not deterministic in safe mode"

    # case02/03/04/05/07/08은 scenario 기반 결정성을 case-specific 단위 테스트가
    # 이미 담당 (예: tests/test_case02.py 등). 본 메타 테스트는 ``external_apis``
    # 목록 자체의 stability와 AI 두 케이스 (가장 확률적인) 결정성을 잠금.


def _check_case09_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> bool:
    """case09 safe mode + faked AI → 2회 결과 byte-identical (T38: config["incoming_message"])."""
    from cases.case09_ai_email_drafter import scenario
    from core.ai import client as ai_client

    fake = json.dumps([{"option": 1, "subject": "S", "body": "B"}], ensure_ascii=False)
    monkeypatch.setattr(ai_client, "chat", lambda messages, **k: fake)

    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"
    incoming = "제목: T\n본문: B"
    r1 = scenario.run(output_dir=out1, config={"incoming_message": incoming})
    r2 = scenario.run(output_dir=out2, config={"incoming_message": incoming})
    text1 = r1["output_files"][0].read_text(encoding="utf-8")
    text2 = r2["output_files"][0].read_text(encoding="utf-8")
    return text1 == text2


def _check_case10_deterministic(tmp_path: Path) -> bool:
    """case10 safe mode → ``_safe_summary`` deterministic dummy 활용."""
    from cases.case10_ai_meeting_summarizer import scenario

    in_dir = tmp_path / "in"
    in_dir.mkdir(parents=True)
    (in_dir / "m000.txt").write_text("같은 본문", encoding="utf-8")
    meta = [{"filename": "m000.txt", "attendees": ["김사장"]}]
    (in_dir / scenario.DEFAULT_META_FILENAME).write_text(
        json.dumps(meta, ensure_ascii=False), encoding="utf-8"
    )

    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"
    scenario.run(input_dir=in_dir, output_dir=out1)
    scenario.run(input_dir=in_dir, output_dir=out2)
    md1 = (out1 / "meeting_summary_m000.md").read_text(encoding="utf-8")
    md2 = (out2 / "meeting_summary_m000.md").read_text(encoding="utf-8")

    # markdown 안에 ``## 요약`` 섹션 본문이 동일해야 함 (오늘 날짜는 다른 줄에
    # 들어가지만 동일 호출 안에선 같은 일자라 일치). 만약 자정에 걸치는
    # 케이스라면 두 호출 사이 시점에서 갈리는데, 실용상 무시.
    return md1 == md2


# --- 3. runner.py --check exits 0 -----------------------------------------


def test_runner_check_exits_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """DoD: ``runner.py --check`` (non-strict) exits 0 on a clean checkout.

    Non-strict 는 키 누락을 warning으로만 처리 → 시드만 있으면 0 exit.
    """
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/x/y")
    result = subprocess.run(
        [sys.executable, "runner.py", "--check"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"DoD gap: runner.py --check exit={result.returncode}\nstderr={result.stderr}"
    )


def test_runner_check_strict_argparse_accepted() -> None:
    """DoD: ``runner.py --check --strict`` 가 argparse에 등록돼 있다.

    strict 통과 여부는 환경에 따라 다르므로 종료코드는 검증하지 않고 (--check
    --strict 가 unknown argument로 거부되지 않음만) 검증한다.
    """
    result = subprocess.run(
        [sys.executable, "runner.py", "--help"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=30,
    )
    assert result.returncode == 0
    assert "--check" in result.stdout
    assert "--strict" in result.stdout, (
        f"DoD gap: --strict not in help output\nstdout={result.stdout}"
    )


# --- 4. ruff check clean ---------------------------------------------------


def test_ruff_check_clean() -> None:
    """DoD R3-H1: ruff check clean across the entire repository.

    Lint cleanliness is part of DoD, not optional. Slow-but-correct.
    """
    result = subprocess.run(
        ["uv", "run", "ruff", "check", "."],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"DoD gap: ruff check failed\n--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )


def test_ruff_format_check_clean() -> None:
    """DoD R3-H1: ruff format --check clean (no formatting drift)."""
    result = subprocess.run(
        ["uv", "run", "ruff", "format", "--check", "."],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"DoD gap: ruff format --check failed\n--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )


# --- 5. mypy --strict on production lock ----------------------------------


def test_mypy_strict_no_errors_on_locked_files(capsys: pytest.CaptureFixture[str]) -> None:
    """DoD: mypy --strict on the cumulative production lock (core/ + runner.py + cases/).

    Tests directories are not part of the production lock — separate cumulative
    debt. This test prints the file count for T26 README sync.
    """
    result = subprocess.run(
        ["uv", "run", "mypy", "--strict", "core", "runner.py", "cases"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=120,
    )
    # mypy의 "Success: ..." 메시지에서 파일 수를 추출 → 메모리/README 동기화에 활용.
    summary = result.stdout.strip().splitlines()[-1] if result.stdout else ""
    file_count = _extract_mypy_file_count(summary)
    print(f"\n[DoD measurement] mypy --strict locked file count: {file_count}")
    print(f"[DoD measurement] mypy summary line: {summary!r}")

    assert result.returncode == 0, (
        f"DoD gap: mypy --strict failed\n--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )


def _extract_mypy_file_count(summary_line: str) -> int | None:
    """mypy ``Success: no issues found in N source files`` → N (없으면 None)."""
    m = re.search(r"in (\d+) source files?", summary_line)
    return int(m.group(1)) if m else None


# --- 6. external usage promise documented ---------------------------------


def test_external_usage_promise_documented() -> None:
    """DoD R1-C2: ``specs/phase2-external-usage-promise.md`` 약속 명시.

    Phase 2 종료 후 1주 안에 실 미팅·강의에서 1회 이상 시연하겠다는 commitment
    가 spec 안에 잠겨야 한다. 약속 충족 시 본 파일에 row append.
    """
    promise_path = PROJECT_ROOT / "specs" / "phase2-external-usage-promise.md"
    assert promise_path.exists(), f"DoD gap: external usage promise doc missing at {promise_path}"
    content = promise_path.read_text(encoding="utf-8")

    # 핵심 commitment 어휘
    assert "Phase 2" in content
    assert "1주" in content, "DoD gap: '1주' commitment timeframe not stated"
    assert "시연" in content, "DoD gap: '시연' (demonstration) keyword not present"
    # status tracking 섹션 존재
    assert "Status" in content or "상태" in content, "DoD gap: status tracking section not present"


# --- 7. discord secrets_mask integration ---------------------------------


def test_discord_webhook_url_masked_when_logged() -> None:
    """DoD: Discord webhook URL이 secrets_mask로 보호되는지 sanity check.

    R2 방어선 — webhook URL 전체가 로그/예외에 leak 되면 안 됨.
    """
    from core.common import secrets_mask

    raw = "https://discord.com/api/webhooks/123456789/abcdefghijklmnopqrstuvwxyz"
    masked = secrets_mask.mask(raw)
    # mask 함수가 raw URL을 그대로 반환하면 보호 실패
    assert masked != raw, "DoD gap: secrets_mask did not mask discord webhook URL"
    # 일부 prefix는 보존되더라도 token 부분은 가려져야 함
    assert "abcdefghijklmnopqrstuvwxyz" not in masked, (
        f"DoD gap: webhook token leaked in masked output: {masked!r}"
    )


# --- 8. email build_message yields valid EmailMessage --------------------


def test_email_build_message_returns_email_message() -> None:
    """DoD: case03 의존 ``email.build_message`` 가 valid ``EmailMessage`` 반환.

    Cross-cutting integration — case03 scenario는 이 객체 위에서 동작.
    """
    import os

    os.environ["GMAIL_SENDER"] = "ax-sales@example.com"
    from core.messaging import email as email_mod

    msg = email_mod.build_message(
        to="recipient@example.com",
        subject="DoD subject",
        body_text="DoD body",
    )
    assert isinstance(msg, EmailMessage)
    assert msg["To"] == "recipient@example.com"
    assert msg["Subject"] == "DoD subject"
