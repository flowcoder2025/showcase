"""Phase 2 DoD verification — messaging cases (case03/case04).

Integration-level checks that complement (not replace) the per-case tests in
``tests/test_case03_email_dispatch.py`` and ``tests/test_case04_overdue_alert.py``.

DoD criteria (per ``specs/2026-05-01-phase2-plan.md`` lines 1890-1900):
- case03: 50건 dispatch + PDF 첨부
- case04: 4단계 분기 모두 실행
- discord secrets_mask 검증
- email send safe_mode + 폴백 경로

All tests run in safe_mode (no real Discord/Gmail calls).
"""

from __future__ import annotations

import inspect
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

# --- helpers ---------------------------------------------------------------


def _stub_pdf_ok(md_path: Path | str, out_path: Path | str, **_kw: Any) -> None:
    """md_to_pdf stub — 빈 PDF 더미 작성 (case03 시나리오 첨부 분기 검증용)."""
    Path(out_path).write_bytes(b"%PDF-1.4\n%dod-stub")


def _safe_send_result(msg: EmailMessage, **_kw: Any) -> dict[str, Any]:
    """email.send stub returning safe-fallback SendResult shape."""
    return {
        "transport": "safe-fallback",
        "sent": False,
        "to": str(msg["To"] or ""),
        "message_id": None,
        "note": "dod test stub",
    }


@pytest.fixture
def case03_seed_input(tmp_path: Path) -> Path:
    """Real 50-row seed used by case03 demo (T38: input_dir 형태로 변환)."""
    p = Path("personas/sample_data/quote_dispatch_list.xlsx")
    if not p.exists():
        pytest.skip(f"DoD gap: seed file missing at {p}")
    in_dir = tmp_path / "case03_in"
    in_dir.mkdir()
    (in_dir / "quote_dispatch_list.xlsx").write_bytes(p.read_bytes())
    return in_dir


@pytest.fixture
def case04_seed_input(tmp_path: Path) -> Path:
    """Real 60-row seed (24/18/12/6 4-level split) used by case04 demo (T38: input_dir)."""
    p = Path("personas/sample_data/overdue_invoices.xlsx")
    if not p.exists():
        pytest.skip(f"DoD gap: seed file missing at {p}")
    in_dir = tmp_path / "case04_in"
    in_dir.mkdir()
    (in_dir / "overdue_invoices.xlsx").write_bytes(p.read_bytes())
    return in_dir


@pytest.fixture(autouse=True)
def _gmail_sender_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """case03 build_message requires GMAIL_SENDER. Apply globally to this module."""
    monkeypatch.setenv("GMAIL_SENDER", "ax-sales@example.com")


@pytest.fixture(autouse=True)
def _isolate_demo_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure DEMO_SAFE state doesn't leak between tests."""
    monkeypatch.delenv("DEMO_SAFE", raising=False)


# --- case03 DoD: 50건 dispatch + PDF 첨부 ---------------------------------


def test_case03_dispatches_50_emails_safe_mode(
    case03_seed_input: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DoD: case03 시나리오가 실제 시드(50건)에 대해 50건 dispatch 처리.

    safe_mode 강제 후 외부 호출(pdf, email.send)을 stub. summary["sent"] == 50을
    확인 — DoD의 "50건 dispatch" 절대 기준.
    """
    monkeypatch.setenv("DEMO_SAFE", "1")
    from cases.case03_email_quote_dispatch import scenario
    from core.docgen import pdf as pdf_mod
    from core.messaging import email as email_mod

    captured: list[EmailMessage] = []

    def capture_send(msg: EmailMessage, **kw: Any) -> dict[str, Any]:
        captured.append(msg)
        return _safe_send_result(msg, **kw)

    monkeypatch.setattr(pdf_mod, "md_to_pdf", _stub_pdf_ok)
    monkeypatch.setattr(email_mod, "send", capture_send)

    out = tmp_path / "out"
    result = scenario.run(input_dir=case03_seed_input, output_dir=out)

    assert result["metrics"]["built"] == 50, (
        f"DoD gap: built={result['metrics']['built']}, expected 50"
    )
    assert result["metrics"]["sent"] == 50, (
        f"DoD gap: sent={result['metrics']['sent']}, expected 50"
    )
    assert result["metrics"]["errors"] == 0
    assert len(captured) == 50


def test_case03_pdf_attachment_present_in_messages(tmp_path: Path) -> None:
    """DoD: build_message 결과 EmailMessage에 application/pdf 첨부가 포함."""
    from core.messaging import email as email_mod

    pdf_path = tmp_path / "quote.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%dod-attach-test")

    msg = email_mod.build_message(
        to="recipient@example.com",
        subject="[Q-DOD-001] DoD attach test",
        body_text="DoD body text",
        body_html="<p>DoD body html</p>",
        attachments=[pdf_path],
    )

    pdf_attachments = [
        part for part in msg.iter_attachments() if part.get_content_type() == "application/pdf"
    ]
    assert len(pdf_attachments) == 1, (
        f"DoD gap: expected 1 application/pdf attachment, got {len(pdf_attachments)}"
    )
    assert pdf_attachments[0].get_filename() == "quote.pdf"


def test_case03_safe_mode_uses_fallback_path_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DoD: Gmail/SMTP credentials 미설정 시 ``send`` 가 safe-fallback으로 graceful degrade.

    실제 네트워크 호출 없이 ``SendResult(transport="safe-fallback", sent=False)``
    를 반환해야 한다. Gmail OAuth + SMTP env 모두 제거 + DEMO_SAFE 미설정 →
    auto-safe 경로로 진입한다.
    """
    monkeypatch.delenv("DEMO_SAFE", raising=False)
    for key in (
        "GMAIL_OAUTH_CREDENTIALS",
        "SMTP_HOST",
        "SMTP_USER",
        "SMTP_PASS",
        "SMTP_PORT",
    ):
        monkeypatch.delenv(key, raising=False)

    from core.messaging import email as email_mod

    msg = email_mod.build_message(
        to="recipient@example.com",
        subject="dod fallback test",
        body_text="body",
    )
    result = email_mod.send(msg)

    assert result["transport"] == "safe-fallback"
    assert result["sent"] is False
    assert result["to"] == "recipient@example.com"
    assert result["note"] is not None


# --- case04 DoD: 4단계 분기 모두 실행 -------------------------------------


def test_case04_runs_all_four_levels(
    case04_seed_input: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DoD: 4단계(friendly/neutral/strict/final) 모두 최소 1회 이상 트리거."""
    monkeypatch.setenv("DEMO_SAFE", "1")
    from cases.case04_discord_overdue_alert import scenario
    from core.messaging import discord

    captured_levels: list[str] = []

    def capture(**kwargs: Any) -> dict[str, int]:
        level = kwargs.get("level", "")
        captured_levels.append(str(level))
        return {"status": 204}

    monkeypatch.setattr(discord, "send_with_level", capture)

    result = scenario.run(input_dir=case04_seed_input)

    by_level = result["extras"]["by_level"]
    assert set(by_level.keys()) == {"friendly", "neutral", "strict", "final"}, (
        f"DoD gap: missing levels — by_level={by_level!r}"
    )
    for level in ("friendly", "neutral", "strict", "final"):
        assert by_level[level] >= 1, (
            f"DoD gap: level={level} not triggered (count={by_level[level]})"
        )
    assert set(captured_levels) == {"friendly", "neutral", "strict", "final"}


def test_case04_seed_distribution(case04_seed_input: Path) -> None:
    """DoD: 60건 시드가 24/18/12/6 분포 (friendly/neutral/strict/final)를 만족."""
    df = pd.read_excel(case04_seed_input / "overdue_invoices.xlsx")
    assert len(df) == 60, f"DoD gap: seed has {len(df)} rows, expected 60"

    from cases.case04_discord_overdue_alert.scenario import classify_level

    counts: dict[str, int] = {"friendly": 0, "neutral": 0, "strict": 0, "final": 0}
    for days in df["연체일"]:
        counts[classify_level(int(days))] += 1

    assert counts == {"friendly": 24, "neutral": 18, "strict": 12, "final": 6}, (
        f"DoD gap: distribution mismatch — got {counts!r}"
    )


# --- discord secrets_mask 검증 --------------------------------------------


def test_discord_webhook_url_masked_in_logs() -> None:
    """DoD: secrets_mask.mask_text가 Discord webhook URL의 토큰 부분을 마스킹.

    ``DISCORD_WEBHOOK_RE`` 패턴이 prefix만 보존하고 path 토큰은 ``***`` 로 치환.
    """
    from core.common import secrets_mask

    sentinel_token = "secret_token_test_XYZ"
    full_url = "https://discord.com/api/webhooks/123456789012345/" + sentinel_token
    raw_log_line = f"sending to webhook: {full_url} now"

    masked = secrets_mask.mask_text(raw_log_line)

    assert sentinel_token not in masked, f"DoD gap: token leaked in masked output: {masked!r}"
    assert "123456789012345" not in masked, f"DoD gap: webhook id leaked: {masked!r}"
    assert "https://discord.com/api/webhooks/" in masked
    assert "***" in masked


def test_discord_send_logs_do_not_leak_url(
    case04_seed_input: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """DoD: case04 safe-mode 실행 중 demo_logger 출력에 raw webhook URL 미노출.

    secrets_mask가 demo_logger 경로(``DemoLogger._format``)에 자동 적용되는지
    end-to-end 확인 — webhook URL을 환경변수로 설정한 후 시나리오를 돌려
    captured stdout에 token 부분이 등장하지 않음을 검증.
    """
    sentinel_token = "leak_canary_DO_NOT_LOG_abcdef123"
    sentinel_url = "https://discord.com/api/webhooks/987654321098765/" + sentinel_token
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", sentinel_url)
    monkeypatch.setenv("DEMO_SAFE", "1")

    from cases.case04_discord_overdue_alert import scenario
    from core.messaging import discord

    # send_with_level stub — 실제 네트워크 호출 차단. 시나리오 코드 자체의
    # demo_logger 경로 (timer.measure success/info 라인 등)를 검사 대상으로 본다.
    monkeypatch.setattr(discord, "send_with_level", lambda **_k: {"status": 204})

    scenario.run(input_dir=case04_seed_input)

    out = capsys.readouterr()
    combined = out.out + out.err
    assert sentinel_token not in combined, (
        f"DoD gap: webhook token leaked to stdout/stderr (length={len(combined)})"
    )
    assert "987654321098765" not in combined, "DoD gap: webhook id leaked to stdout/stderr"


# --- email send safe_mode + fallback 경로 ---------------------------------


def test_email_send_safe_mode_returns_dummy(monkeypatch: pytest.MonkeyPatch) -> None:
    """DoD: ``DEMO_SAFE=1`` 시 ``email.send`` 가 즉시 safe-fallback 반환, 네트워크 호출 0회.

    SendResult 필수 필드(transport/sent/to/message_id/note)를 모두 갖추고
    ``transport == 'safe-fallback'`` + ``sent == False`` 가 보장되어야 한다.
    """
    monkeypatch.setenv("DEMO_SAFE", "1")
    # 네트워크 호출이 발생하면 즉시 실패하도록 transport helper를 오염시킨다.
    from core.messaging import email as email_mod

    def _explode_gmail(*_a: Any, **_kw: Any) -> Any:
        raise AssertionError("DoD gap: _send_gmail_api invoked under DEMO_SAFE=1")

    def _explode_smtp(*_a: Any, **_kw: Any) -> Any:
        raise AssertionError("DoD gap: _send_smtp invoked under DEMO_SAFE=1")

    monkeypatch.setattr(email_mod, "_send_gmail_api", _explode_gmail)
    monkeypatch.setattr(email_mod, "_send_smtp", _explode_smtp)

    msg = email_mod.build_message(
        to="recipient@example.com",
        subject="dod safe mode test",
        body_text="body",
    )
    result = email_mod.send(msg)

    # SendResult shape — 모든 필수 필드가 존재.
    for key in ("transport", "sent", "to", "message_id", "note"):
        assert key in result, f"DoD gap: SendResult missing {key!r}"
    assert result["transport"] == "safe-fallback"
    assert result["sent"] is False
    assert result["to"] == "recipient@example.com"
    assert result["note"] is not None and "DEMO_SAFE" in result["note"]


def test_email_send_fallback_chain_documented() -> None:
    """DoD: ``core/messaging/email.py`` 가 Gmail API + SMTP 두 transport 경로 모두 보유.

    fallback chain의 양 끝점이 코드에 존재함을 ``inspect`` 로 정적 확인 —
    ``_send_gmail_api`` 와 ``_send_smtp`` helper가 모두 정의되어 있어야 한다.
    또한 ``send`` 의 transport literal에 ``"gmail_api"`` 와 ``"smtp"`` 가 모두
    선택지로 들어있어야 한다.
    """
    from core.messaging import email as email_mod

    assert hasattr(email_mod, "_send_gmail_api"), "DoD gap: Gmail API path missing"
    assert hasattr(email_mod, "_send_smtp"), "DoD gap: SMTP fallback path missing"
    assert callable(email_mod._send_gmail_api)
    assert callable(email_mod._send_smtp)

    # send() body must reference both transports for auto-selection logic.
    src = inspect.getsource(email_mod.send)
    assert "gmail_api" in src, "DoD gap: send() does not branch on gmail_api"
    assert "smtp" in src, "DoD gap: send() does not branch on smtp"
    assert "safe-fallback" in src, (
        "DoD gap: send() lacks safe-fallback branch — DEMO_SAFE may not short-circuit"
    )
