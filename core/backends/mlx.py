"""MLX-backed OCR implementation (delegates to `core.ocr.gemma`).

Caching is layered on top via `core.backends.cached.CachedOCRBackend`.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, cast

from core.common.demo_logger import demo_logger
from core.ocr import gemma
from core.ocr.gemma import ModelLiteral


class MLXOCRBackend:
    def __init__(self, base_url: str, *, api_key: str | None = None) -> None:
        self._base_url = base_url
        self._api_key = api_key

    def cache_identity(self) -> str:
        """R1-H5: secret-free fingerprint (api_key는 sha256 후 8자만 포함)."""
        key_hash = hashlib.sha256((self._api_key or "").encode()).hexdigest()[:8]
        raw = f"mlx|{self._base_url}|{key_hash}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def extract(
        self,
        image_path: Path | str,
        *,
        model: str,
        schema: dict[str, Any] | None = None,
        prompt: str | None = None,
    ) -> dict[str, Any]:
        demo_logger("backends.mlx").info(f"MLX OCR: model={model}, image={image_path}")
        return gemma.extract(
            image_path,
            model=cast(ModelLiteral, model),
            schema=schema,
            prompt=prompt,
        )
