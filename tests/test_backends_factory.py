"""T36 — `default_backends()` / `safe_backends()` factory + `_DefaultMessagingBackend` (R2-L1)."""

from __future__ import annotations

from cases._protocols import AIBackend, Backends, MessagingBackend, OCRBackend
from core.backends.discord import DiscordWebhookBackend
from core.backends.factory import (
    _DefaultMessagingBackend,
    default_backends,
    safe_backends,
)
from core.backends.gmail import GmailBackend


def test_default_backends_returns_backends_dataclass() -> None:
    bk = default_backends()
    assert isinstance(bk, Backends)


def test_default_backends_components_satisfy_protocols() -> None:
    bk = default_backends()
    assert isinstance(bk.ocr, OCRBackend)
    assert isinstance(bk.ai, AIBackend)
    assert isinstance(bk.msg, MessagingBackend)


def test_safe_backends_returns_backends_dataclass() -> None:
    bk = safe_backends()
    assert isinstance(bk, Backends)


def test_safe_backends_components_satisfy_protocols() -> None:
    bk = safe_backends()
    assert isinstance(bk.ocr, OCRBackend)
    assert isinstance(bk.ai, AIBackend)
    assert isinstance(bk.msg, MessagingBackend)


def test_default_messaging_satisfies_protocol() -> None:
    msg = _DefaultMessagingBackend(
        discord=DiscordWebhookBackend(webhook_url="https://discord.com/api/webhooks/x/y"),
        gmail=GmailBackend(token="ya29.fake"),
    )
    assert isinstance(msg, MessagingBackend)


def test_default_messaging_cache_identity_combines_components() -> None:
    msg = _DefaultMessagingBackend(
        discord=DiscordWebhookBackend(webhook_url="https://discord.com/api/webhooks/x/y"),
        gmail=GmailBackend(token="ya29.fake"),
    )
    identity = msg.cache_identity()
    assert "|" in identity
