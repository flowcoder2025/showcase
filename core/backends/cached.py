"""Cache decorators (R2-C3) — OCR, AI, Messaging 모두 cover.

cache key: sha256(case_id + backend_fingerprint + args_repr) — sha1 collision
방지 (R1-M3). underlying backend는 `cache_identity()` 메서드를 제공해야 한다
(R1-H5 — `__dict__` repr 기반 fingerprint 회피).

OCR/AI: cache hit → 외부 호출 skip + 저장된 응답 반환.
Messaging: cache marker → idempotent skip (같은 args 두 번이면 두 번째는 send 안 함).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cases._protocols import AIBackend, MessagingBackend, OCRBackend


def _key(case_id: str, identity: str, args_repr: str) -> str:
    return hashlib.sha256(f"{case_id}|{identity}|{args_repr}".encode()).hexdigest()[:32]


def _identity_of(real: object) -> str:
    method = getattr(real, "cache_identity", None)
    if callable(method):
        result = method()
        if isinstance(result, str):
            return result
    return "unknown"


class CachedOCRBackend:
    def __init__(self, real: OCRBackend, store: Path, *, case_id: str) -> None:
        self._real = real
        self._store = store
        self._case_id = case_id
        self._identity = _identity_of(real)
        self._store.mkdir(parents=True, exist_ok=True)

    def cache_identity(self) -> str:
        return self._identity

    def extract(
        self,
        image_path: Path | str,
        *,
        model: str,
        schema: dict[str, Any] | None = None,
        prompt: str | None = None,
    ) -> dict[str, Any]:
        args_repr = json.dumps(
            {
                "img": str(image_path),
                "model": model,
                "schema": schema,
                "prompt": prompt,
            },
            sort_keys=True,
            default=str,
        )
        key = _key(self._case_id, self._identity, args_repr)
        cache_file = self._store / f"{key}.json"
        if cache_file.exists():
            cached: dict[str, Any] = json.loads(cache_file.read_text(encoding="utf-8"))
            return cached
        result = self._real.extract(image_path, model=model, schema=schema, prompt=prompt)
        cache_file.write_text(
            json.dumps(result, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        return result


class CachedAIBackend:
    def __init__(self, real: AIBackend, store: Path, *, case_id: str) -> None:
        self._real = real
        self._store = store
        self._case_id = case_id
        self._identity = _identity_of(real)
        self._store.mkdir(parents=True, exist_ok=True)

    def cache_identity(self) -> str:
        return self._identity

    def chat(self, messages: list[dict[str, str]], *, model: str | None = None) -> str:
        args_repr = json.dumps({"messages": messages, "model": model}, sort_keys=True, default=str)
        key = _key(self._case_id, self._identity, args_repr)
        cache_file = self._store / f"{key}.json"
        if cache_file.exists():
            payload = json.loads(cache_file.read_text(encoding="utf-8"))
            response = payload["response"]
            assert isinstance(response, str)
            return response
        result = self._real.chat(messages, model=model)
        cache_file.write_text(
            json.dumps({"response": result}, ensure_ascii=False),
            encoding="utf-8",
        )
        return result


class CachedMessagingBackend:
    """Messaging은 부수효과 (외부 발송) — cache는 idempotency 추적만.

    같은 args 두 번이면 두 번째는 send skip. cache hit 판정은 marker file 존재.
    """

    def __init__(self, real: MessagingBackend, store: Path, *, case_id: str) -> None:
        self._real = real
        self._store = store
        self._case_id = case_id
        self._identity = _identity_of(real)
        self._store.mkdir(parents=True, exist_ok=True)

    def cache_identity(self) -> str:
        return self._identity

    def send_discord(self, content: str, *, level: str) -> None:
        args_repr = json.dumps({"d": content, "l": level}, sort_keys=True)
        key = _key(self._case_id, self._identity, args_repr)
        marker = self._store / f"{key}.sent"
        if marker.exists():
            return
        self._real.send_discord(content, level=level)
        marker.write_text("", encoding="utf-8")

    def send_email(self, message: Any) -> None:
        key = _key(self._case_id, self._identity, repr(message))
        marker = self._store / f"{key}.sent"
        if marker.exists():
            return
        self._real.send_email(message)
        marker.write_text("", encoding="utf-8")
