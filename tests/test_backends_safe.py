"""T36 — Safe* backends deterministic dummy returns (외부 호출 0)."""

from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path

from cases._protocols import AIBackend, MessagingBackend, OCRBackend
from core.backends.safe import SafeAIBackend, SafeMessagingBackend, SafeOCRBackend


def test_safe_ocr_satisfies_protocol() -> None:
    assert isinstance(SafeOCRBackend(), OCRBackend)


def test_safe_ai_satisfies_protocol() -> None:
    assert isinstance(SafeAIBackend(), AIBackend)


def test_safe_messaging_satisfies_protocol() -> None:
    assert isinstance(SafeMessagingBackend(), MessagingBackend)


def test_safe_ocr_returns_safe_dummy(tmp_path: Path) -> None:
    img = tmp_path / "x.png"
    img.write_bytes(b"")
    result = SafeOCRBackend().extract(img, model="gemma4:e2b")
    assert result.get("_safe") is True
    assert "items" in result
    assert "total" in result


def test_safe_ai_returns_dummy_string() -> None:
    response = SafeAIBackend().chat([{"role": "user", "content": "hi"}])
    assert isinstance(response, str)
    assert "[SAFE-DUMMY]" in response


def test_safe_messaging_send_discord_no_op() -> None:
    """부수효과 없음 — return None, raise 없음."""
    result = SafeMessagingBackend().send_discord("test", level="info")
    assert result is None


def test_safe_messaging_send_email_no_op() -> None:
    msg = EmailMessage()
    msg["From"] = "a@b.com"
    msg["To"] = "c@d.com"
    msg["Subject"] = "test"
    result = SafeMessagingBackend().send_email(msg)
    assert result is None


def test_safe_ocr_cache_identity_deterministic() -> None:
    a = SafeOCRBackend().cache_identity()
    b = SafeOCRBackend().cache_identity()
    assert a == b == "safe-ocr-deterministic"


def test_safe_ai_cache_identity_deterministic() -> None:
    assert SafeAIBackend().cache_identity() == "safe-ai-deterministic"


def test_safe_messaging_cache_identity_deterministic() -> None:
    assert SafeMessagingBackend().cache_identity() == "safe-msg-deterministic"
