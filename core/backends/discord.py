"""Discord webhook backend (delegates to `core.messaging.discord`).

`MessagingBackend` Protocol의 `send_email`은 본 backend가 제공하지 않는다 —
`_DefaultMessagingBackend`가 Discord + Gmail을 합쳐 Protocol을 만족시킨다.
"""

from __future__ import annotations

import hashlib

from core.common.demo_logger import demo_logger
from core.messaging import discord


class DiscordWebhookBackend:
    def __init__(self, webhook_url: str) -> None:
        self._webhook_url = webhook_url

    def cache_identity(self) -> str:
        """R1-H5: webhook URL sha256 후 16자만 노출."""
        return hashlib.sha256(f"discord|{self._webhook_url}".encode()).hexdigest()[:16]

    def send_discord(self, content: str, *, level: str) -> None:
        demo_logger("backends.discord").info(f"Discord send: level={level}")
        discord.send(content, level=level, webhook_url=self._webhook_url)
