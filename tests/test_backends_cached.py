"""T36 — Cached{OCR,AI,Messaging}Backend (R2-C3) cache hit/miss + idempotent send."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.backends.cached import (
    CachedAIBackend,
    CachedMessagingBackend,
    CachedOCRBackend,
)


class _FakeOCR:
    """records calls; returns increasing payload to detect hit vs miss."""

    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    def cache_identity(self) -> str:
        return "fake-ocr-id"

    def extract(
        self,
        image_path: Path | str,
        *,
        model: str,
        schema: dict[str, Any] | None = None,
        prompt: str | None = None,
    ) -> dict[str, Any]:
        self.calls.append((str(image_path), model, schema, prompt))
        return {"hit_count": len(self.calls), "items": []}


class _FakeAI:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    def cache_identity(self) -> str:
        return "fake-ai-id"

    def chat(self, messages: list[dict[str, str]], *, model: str | None = None) -> str:
        self.calls.append((messages, model))
        return f"call#{len(self.calls)}"


class _FakeMsg:
    def __init__(self) -> None:
        self.discord_calls: list[tuple[str, str]] = []
        self.email_calls: list[Any] = []

    def cache_identity(self) -> str:
        return "fake-msg-id"

    def send_discord(self, content: str, *, level: str) -> None:
        self.discord_calls.append((content, level))

    def send_email(self, message: Any) -> None:
        self.email_calls.append(message)


def test_cached_ocr_first_call_misses(tmp_path: Path) -> None:
    real = _FakeOCR()
    cached = CachedOCRBackend(real, tmp_path / "store", case_id="case07")
    img = tmp_path / "img.png"
    img.write_bytes(b"")
    result = cached.extract(img, model="gemma4:e2b")
    assert result["hit_count"] == 1
    assert len(real.calls) == 1


def test_cached_ocr_second_same_call_hits(tmp_path: Path) -> None:
    real = _FakeOCR()
    cached = CachedOCRBackend(real, tmp_path / "store", case_id="case07")
    img = tmp_path / "img.png"
    img.write_bytes(b"")
    cached.extract(img, model="gemma4:e2b")
    second = cached.extract(img, model="gemma4:e2b")
    assert second["hit_count"] == 1  # 캐시 hit — 두 번째는 1번 호출 결과
    assert len(real.calls) == 1


def test_cached_ocr_different_model_misses(tmp_path: Path) -> None:
    real = _FakeOCR()
    cached = CachedOCRBackend(real, tmp_path / "store", case_id="case07")
    img = tmp_path / "img.png"
    img.write_bytes(b"")
    cached.extract(img, model="gemma4:e2b")
    cached.extract(img, model="gemma4:e4b")
    assert len(real.calls) == 2


def test_cached_ocr_persists_to_disk(tmp_path: Path) -> None:
    store = tmp_path / "store"
    real = _FakeOCR()
    cached = CachedOCRBackend(real, store, case_id="case07")
    img = tmp_path / "img.png"
    img.write_bytes(b"")
    cached.extract(img, model="gemma4:e2b")
    files = list(store.glob("*.json"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert payload["hit_count"] == 1


def test_cached_ai_hit_returns_response(tmp_path: Path) -> None:
    real = _FakeAI()
    cached = CachedAIBackend(real, tmp_path / "store", case_id="case10")
    msgs = [{"role": "user", "content": "hi"}]
    cached.chat(msgs, model="gemini-2.5-flash")
    second = cached.chat(msgs, model="gemini-2.5-flash")
    assert second == "call#1"
    assert len(real.calls) == 1


def test_cached_ai_distinguishes_messages(tmp_path: Path) -> None:
    real = _FakeAI()
    cached = CachedAIBackend(real, tmp_path / "store", case_id="case10")
    cached.chat([{"role": "user", "content": "a"}], model="m")
    cached.chat([{"role": "user", "content": "b"}], model="m")
    assert len(real.calls) == 2


def test_cached_messaging_idempotent_skip(tmp_path: Path) -> None:
    """같은 args 두 번 → 두 번째는 send 안 함."""
    real = _FakeMsg()
    cached = CachedMessagingBackend(real, tmp_path / "store", case_id="case04")
    cached.send_discord("hi", level="info")
    cached.send_discord("hi", level="info")
    assert len(real.discord_calls) == 1


def test_cached_messaging_different_content_resends(tmp_path: Path) -> None:
    real = _FakeMsg()
    cached = CachedMessagingBackend(real, tmp_path / "store", case_id="case04")
    cached.send_discord("hi", level="info")
    cached.send_discord("bye", level="info")
    assert len(real.discord_calls) == 2


def test_cached_messaging_email_idempotent(tmp_path: Path) -> None:
    real = _FakeMsg()
    cached = CachedMessagingBackend(real, tmp_path / "store", case_id="case03")
    cached.send_email("msg-1")
    cached.send_email("msg-1")
    assert len(real.email_calls) == 1


def test_cached_creates_store_dir(tmp_path: Path) -> None:
    """store 디렉토리 존재 안 해도 자동 생성."""
    real = _FakeAI()
    nested = tmp_path / "deep" / "nested" / "store"
    cached = CachedAIBackend(real, nested, case_id="x")
    cached.chat([{"role": "user", "content": "hi"}])
    assert nested.exists()


def test_cached_ocr_cache_identity_proxy(tmp_path: Path) -> None:
    """CachedOCRBackend는 underlying의 identity를 proxy."""
    real = _FakeOCR()
    cached = CachedOCRBackend(real, tmp_path / "store", case_id="case07")
    assert cached.cache_identity() == real.cache_identity()
