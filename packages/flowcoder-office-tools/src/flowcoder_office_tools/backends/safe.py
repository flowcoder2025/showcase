"""Deterministic safe-mode backends — 외부 호출 0, dummy 반환만.

`safe_backends()` factory가 사용. cache_identity는 deterministic literal —
caching layer가 same-input → same-output을 안정 보장한다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class SafeOCRBackend:
    def cache_identity(self) -> str:
        return "safe-ocr-deterministic"

    def extract(
        self,
        image_path: Path | str,
        *,
        model: str,
        schema: dict[str, Any] | None = None,
        prompt: str | None = None,
    ) -> dict[str, Any]:
        return {"_safe": True, "items": [], "total": 0}


class SafeAIBackend:
    def cache_identity(self) -> str:
        return "safe-ai-deterministic"

    def chat(self, messages: list[dict[str, str]], *, model: str | None = None) -> str:
        return "[SAFE-DUMMY] AI response"


class SafeMessagingBackend:
    def cache_identity(self) -> str:
        return "safe-msg-deterministic"

    def send_discord(self, content: str, *, level: str) -> None:
        pass

    def send_email(self, message: Any) -> None:
        pass
