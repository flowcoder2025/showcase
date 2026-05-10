"""OpenRouter-backed AI implementation (delegates to `core.ai.client`).

Caching is layered via `core.backends.cached.CachedAIBackend`.
"""

from __future__ import annotations

import hashlib
from typing import Any, cast

from core.ai import client
from core.common.demo_logger import demo_logger


class OpenRouterAIBackend:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def cache_identity(self) -> str:
        """R1-H5: api_key sha256 후 16자만 노출."""
        return hashlib.sha256(f"openrouter|{self._api_key}".encode()).hexdigest()[:16]

    def chat(self, messages: list[dict[str, str]], *, model: str | None = None) -> str:
        demo_logger("backends.openrouter").info(
            f"OpenRouter chat: model={model}, messages={len(messages)}"
        )
        return client.chat(cast(list[dict[str, Any]], messages), model=model)
