"""Phase 3-Pkg T46 — Fake backends for dogfood smoke.

Implements :mod:`flowcoder_office_tools.protocols` Protocol surface so external
consumers can verify that the package's DI surface accepts arbitrary
implementations (R3-H1). ``cache_identity()`` mirrors the contract documented
in :mod:`flowcoder_office_tools.backends.cached` — the cache layer fingerprints
the underlying backend by calling this method.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flowcoder_office_tools.protocols import Backends


class FakeOCRBackend:
    def __init__(self) -> None:
        self.calls = 0

    def cache_identity(self) -> str:
        return "fake-ocr"

    def extract(
        self,
        image_path: Path | str,
        *,
        model: str,
        schema: dict[str, Any] | None = None,
        prompt: str | None = None,
    ) -> dict[str, Any]:
        self.calls += 1
        return {"items": [{"name": "fake", "amount": 1000}], "total": 1000}


class FakeAIBackend:
    def cache_identity(self) -> str:
        return "fake-ai"

    def chat(self, messages: list[dict[str, str]], *, model: str | None = None) -> str:
        return "fake response"


class FakeMessagingBackend:
    def cache_identity(self) -> str:
        return "fake-msg"

    def send_discord(self, content: str, *, level: str) -> None:
        pass

    def send_email(self, message: Any) -> None:
        pass


def fake_backends() -> Backends:
    return Backends(
        ocr=FakeOCRBackend(),
        ai=FakeAIBackend(),
        msg=FakeMessagingBackend(),
    )
