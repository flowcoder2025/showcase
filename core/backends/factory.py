"""Backend factories — `default_backends()` for production / `safe_backends()` for safe-mode.

`_DefaultMessagingBackend` (R2-L1) wraps Discord + Gmail providers and presents
the unified `MessagingBackend` Protocol surface. Individual `DiscordWebhookBackend`
and `GmailBackend` deliberately implement only their respective method (Discord
or Email); the unified Protocol is composed here.

Plan v2.1.1 deviation: plan code calls `self._discord.send_with_level(content, level=level)`
which would require a `title` argument (`send_with_level` is the case04
domain-specific helper). Replaced with direct delegation to
`DiscordWebhookBackend.send_discord(content, level=level)` — generic Protocol
satisfaction; case04 keeps using `discord.send_with_level` directly via its
scenario.
"""

from __future__ import annotations

import os
from typing import Any

from cases._protocols import Backends
from core.backends.discord import DiscordWebhookBackend
from core.backends.gmail import GmailBackend
from core.backends.mlx import MLXOCRBackend
from core.backends.openrouter import OpenRouterAIBackend
from core.backends.safe import SafeAIBackend, SafeMessagingBackend, SafeOCRBackend


class _DefaultMessagingBackend:
    """Discord + Gmail provider 통합 wrapper — `MessagingBackend` Protocol 만족."""

    def __init__(
        self,
        *,
        discord: DiscordWebhookBackend,
        gmail: GmailBackend,
    ) -> None:
        self._discord = discord
        self._gmail = gmail

    def cache_identity(self) -> str:
        return f"{self._discord.cache_identity()}|{self._gmail.cache_identity()}"

    def send_discord(self, content: str, *, level: str) -> None:
        self._discord.send_discord(content, level=level)

    def send_email(self, message: Any) -> None:
        self._gmail.send_email(message)


def default_backends() -> Backends:
    return Backends(
        ocr=MLXOCRBackend(
            base_url=os.getenv("AX_OCR_BASE_URL_E2B", "http://localhost:11437"),
        ),
        ai=OpenRouterAIBackend(api_key=os.getenv("OPENROUTER_API_KEY", "")),
        msg=_DefaultMessagingBackend(
            discord=DiscordWebhookBackend(
                webhook_url=os.getenv("DISCORD_WEBHOOK_URL", ""),
            ),
            gmail=GmailBackend(token=os.getenv("GMAIL_OAUTH_TOKEN", "")),
        ),
    )


def safe_backends() -> Backends:
    return Backends(
        ocr=SafeOCRBackend(),
        ai=SafeAIBackend(),
        msg=SafeMessagingBackend(),
    )
