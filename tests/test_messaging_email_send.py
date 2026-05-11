"""Tests for core.messaging.email.send (T7b).

T7b scope: send — Gmail API primary + SMTP fallback + safe-mode short-circuit.

대부분 monkeypatch로 외부 호출을 mock한다. 실제 Gmail API/SMTP 호출 없이
contract만 검증한다. 단일 patch point (INTERCEPT_TARGETS["gmail"] →
core.messaging.email.send) 보존을 위해 모듈 참조 호출 패턴을 강제한다.
"""

from __future__ import annotations

from email.message import EmailMessage
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest
from flowcoder_office_tools.common import safe_mode
from flowcoder_office_tools.messaging import email as email_mod

# --- Helpers ---------------------------------------------------------------


def _basic_msg(to: str = "r@example.com") -> EmailMessage:
    """Build a minimal EmailMessage for send tests (bypasses build_message)."""
    msg = EmailMessage()
    msg["To"] = to
    msg["From"] = "s@example.com"
    msg["Subject"] = "test"
    msg.set_content("body")
    return msg


# --- Safe mode short-circuit -----------------------------------------------


def test_send_safe_mode_short_circuit(monkeypatch: pytest.MonkeyPatch) -> None:
    """DEMO_SAFE=1 이면 외부 호출 없이 즉시 dummy 반환."""
    monkeypatch.setenv("DEMO_SAFE", "1")

    gmail_spy = MagicMock()
    smtp_spy = MagicMock()
    monkeypatch.setattr(email_mod, "_send_gmail_api", gmail_spy)
    monkeypatch.setattr(email_mod, "_send_smtp", smtp_spy)

    result = email_mod.send(_basic_msg())
    assert result["transport"] == "safe-fallback"
    assert result["sent"] is False
    assert result["to"] == "r@example.com"
    assert result["message_id"] is None
    assert result["note"] is not None
    assert "DEMO_SAFE" in result["note"]
    gmail_spy.assert_not_called()
    smtp_spy.assert_not_called()


def test_send_safe_fallback_does_not_invoke_external(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    """DEMO_SAFE=1 이면 GMAIL_OAUTH_CREDENTIALS가 설정돼있어도 호출 안 됨."""
    monkeypatch.setenv("DEMO_SAFE", "1")
    creds = tmp_path / "client_secrets.json"
    creds.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("GMAIL_OAUTH_CREDENTIALS", str(creds))

    gmail_spy = MagicMock()
    monkeypatch.setattr(email_mod, "_send_gmail_api", gmail_spy)

    result = email_mod.send(_basic_msg())
    assert result["transport"] == "safe-fallback"
    gmail_spy.assert_not_called()


# --- Auto transport selection ---------------------------------------------


def test_send_auto_uses_gmail_when_oauth_available(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    monkeypatch.setenv("DEMO_SAFE", "0")
    creds = tmp_path / "client_secrets.json"
    creds.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("GMAIL_OAUTH_CREDENTIALS", str(creds))

    gmail_spy = MagicMock(
        return_value=email_mod.SendResult(
            transport="gmail_api",
            sent=True,
            to="r@example.com",
            message_id="abc123",
            note=None,
        )
    )
    monkeypatch.setattr(email_mod, "_send_gmail_api", gmail_spy)

    result = email_mod.send(_basic_msg())
    assert result["transport"] == "gmail_api"
    assert result["sent"] is True
    assert gmail_spy.call_count == 1


def test_send_auto_falls_back_to_smtp_when_no_gmail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEMO_SAFE", "0")
    monkeypatch.delenv("GMAIL_OAUTH_CREDENTIALS", raising=False)
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "user")
    monkeypatch.setenv("SMTP_PASS", "pass")

    smtp_spy = MagicMock(
        return_value=email_mod.SendResult(
            transport="smtp",
            sent=True,
            to="r@example.com",
            message_id=None,
            note=None,
        )
    )
    monkeypatch.setattr(email_mod, "_send_smtp", smtp_spy)

    result = email_mod.send(_basic_msg())
    assert result["transport"] == "smtp"
    assert smtp_spy.call_count == 1


def test_send_auto_force_safe_when_neither_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEMO_SAFE", "0")
    monkeypatch.delenv("GMAIL_OAUTH_CREDENTIALS", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASS", raising=False)

    result = email_mod.send(_basic_msg())
    assert result["transport"] == "safe-fallback"
    assert result["sent"] is False
    # force_safe should have flipped DEMO_SAFE to "1"
    assert safe_mode.is_safe() is True
    assert "no Gmail" in (result["note"] or "")


# --- Explicit transport ---------------------------------------------------


def test_send_explicit_gmail_without_credentials_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEMO_SAFE", "0")
    monkeypatch.delenv("GMAIL_OAUTH_CREDENTIALS", raising=False)

    with pytest.raises(RuntimeError, match=r"GMAIL_OAUTH_CREDENTIALS"):
        email_mod.send(_basic_msg(), transport="gmail_api")


def test_send_explicit_smtp_without_credentials_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEMO_SAFE", "0")
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASS", raising=False)

    with pytest.raises(RuntimeError, match=r"SMTP"):
        email_mod.send(_basic_msg(), transport="smtp")


def test_send_explicit_safe_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_SAFE", "0")

    gmail_spy = MagicMock()
    smtp_spy = MagicMock()
    monkeypatch.setattr(email_mod, "_send_gmail_api", gmail_spy)
    monkeypatch.setattr(email_mod, "_send_smtp", smtp_spy)

    result = email_mod.send(_basic_msg(), transport="safe-fallback")
    assert result["transport"] == "safe-fallback"
    assert result["sent"] is False
    assert result["note"] == "explicit safe-fallback"
    gmail_spy.assert_not_called()
    smtp_spy.assert_not_called()


def test_send_unknown_transport_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_SAFE", "0")

    with pytest.raises(ValueError, match=r"unknown transport"):
        email_mod.send(_basic_msg(), transport=cast(Any, "invalid"))


# --- Gmail API internals --------------------------------------------------


def test_send_returns_message_id_from_gmail_api_response(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    """_send_gmail_api: googleapiclient 응답의 'id'가 result로 propagate."""
    monkeypatch.setenv("DEMO_SAFE", "0")
    creds_file = tmp_path / "client_secrets.json"
    creds_file.write_text("{}", encoding="utf-8")
    token_file = tmp_path / "token.json"
    token_file.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("GMAIL_OAUTH_CREDENTIALS", str(creds_file))
    monkeypatch.setenv("GMAIL_TOKEN_PATH", str(token_file))

    valid_creds = MagicMock()
    valid_creds.valid = True
    valid_creds.expired = False
    valid_creds.refresh_token = None

    fake_service = MagicMock()
    (
        fake_service.users.return_value.messages.return_value.send.return_value.execute.return_value
    ) = {"id": "abc123", "threadId": "t1"}

    with (
        patch(
            "google.oauth2.credentials.Credentials.from_authorized_user_file",
            return_value=valid_creds,
        ),
        patch("googleapiclient.discovery.build", return_value=fake_service),
    ):
        result = email_mod._send_gmail_api(_basic_msg(), "r@example.com")

    assert result["transport"] == "gmail_api"
    assert result["sent"] is True
    assert result["message_id"] == "abc123"
    assert result["to"] == "r@example.com"


# --- SMTP internals -------------------------------------------------------


def test_send_smtp_uses_starttls_and_login(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_SAFE", "0")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "alice@example.com")
    monkeypatch.setenv("SMTP_PASS", "pw")

    smtp_instance = MagicMock()
    smtp_cm = MagicMock()
    smtp_cm.__enter__ = MagicMock(return_value=smtp_instance)
    smtp_cm.__exit__ = MagicMock(return_value=False)

    msg = _basic_msg()

    with patch("smtplib.SMTP", return_value=smtp_cm) as smtp_cls:
        result = email_mod._send_smtp(msg, "r@example.com")

    smtp_cls.assert_called_once_with("smtp.example.com", 587, timeout=30)
    smtp_instance.starttls.assert_called_once()
    smtp_instance.login.assert_called_once_with("alice@example.com", "pw")
    smtp_instance.send_message.assert_called_once_with(msg)
    assert result["transport"] == "smtp"
    assert result["sent"] is True
    assert result["message_id"] is None
    assert result["to"] == "r@example.com"


# --- Contract / typed dict ------------------------------------------------


def test_send_result_typed_dict_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_SAFE", "1")
    result = email_mod.send(_basic_msg())
    assert set(result.keys()) == {"transport", "sent", "to", "message_id", "note"}


def test_send_to_field_propagated_to_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_SAFE", "1")
    msg = _basic_msg(to="x@y.z")
    result = email_mod.send(msg)
    assert result["to"] == "x@y.z"


# --- safe_mode integration ------------------------------------------------


def test_safe_mode_intercept_can_patch_send(monkeypatch: pytest.MonkeyPatch) -> None:
    """INTERCEPT_TARGETS["gmail"] = (core.messaging.email, send) 단일 patch point.

    safe_mode.intercept(case_id, ["gmail"]) 컨텍스트 안에서 모듈 참조 호출이
    stub으로 우회되는지 검증한다.
    """
    # 1) Registration check
    assert safe_mode.INTERCEPT_TARGETS["gmail"] == (
        "flowcoder_office_tools.messaging.email",
        "send",
    )

    # 2) Patch through intercept and verify modular reference is stubbed
    monkeypatch.setenv("DEMO_SAFE", "1")
    with safe_mode.intercept("test-case", ["gmail"]):
        result = email_mod.send(_basic_msg())
    # Stub returns {"_safe": True, ...}, NOT the real SendResult.
    assert isinstance(result, dict)
    assert result.get("_safe") is True
    assert result.get("qualname") == "flowcoder_office_tools.messaging.email.send"
