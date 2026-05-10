"""T36 — Backend Protocol 만족 + extract signature + cache_identity (R1-H5)."""

from __future__ import annotations

import inspect

from cases._protocols import AIBackend, OCRBackend
from core.backends.discord import DiscordWebhookBackend
from core.backends.gmail import GmailBackend
from core.backends.mlx import MLXOCRBackend
from core.backends.openrouter import OpenRouterAIBackend


def test_mlx_satisfies_ocr_protocol() -> None:
    assert isinstance(MLXOCRBackend(base_url="http://localhost:11437"), OCRBackend)


def test_openrouter_satisfies_ai_protocol() -> None:
    assert isinstance(OpenRouterAIBackend(api_key="dummy"), AIBackend)


def test_mlx_extract_accepts_prompt() -> None:
    """R2-H1: prompt 인자 명시 통과."""
    sig = inspect.signature(MLXOCRBackend.extract)
    assert "prompt" in sig.parameters


def test_mlx_extract_accepts_schema() -> None:
    sig = inspect.signature(MLXOCRBackend.extract)
    assert "schema" in sig.parameters


def test_mlx_extract_accepts_image_path() -> None:
    sig = inspect.signature(MLXOCRBackend.extract)
    assert "image_path" in sig.parameters


def test_openrouter_cache_identity_does_not_expose_secret() -> None:
    """R1-H5: cache_identity()가 api_key를 평문 노출 안 함."""
    api_key = "sk-or-v1-SECRET_FAKE_FOR_IDENTITY_TEST"
    backend = OpenRouterAIBackend(api_key=api_key)
    identity = backend.cache_identity()
    assert api_key not in identity
    assert len(identity) == 16


def test_mlx_cache_identity_does_not_expose_api_key() -> None:
    secret = "internal-mlx-API-KEY-SECRET-FAKE"
    backend = MLXOCRBackend(base_url="http://localhost:11437", api_key=secret)
    identity = backend.cache_identity()
    assert secret not in identity
    assert len(identity) == 16


def test_discord_cache_identity_does_not_expose_webhook_url() -> None:
    sus = "https://discord.com/api/webhooks/123/TOKEN_PART_SECRET_FAKE"
    backend = DiscordWebhookBackend(webhook_url=sus)
    identity = backend.cache_identity()
    assert "TOKEN_PART_SECRET_FAKE" not in identity
    assert len(identity) == 16


def test_gmail_cache_identity_does_not_expose_token() -> None:
    secret = "ya29.GMAIL_OAUTH_TOKEN_SECRET_FAKE"
    backend = GmailBackend(token=secret)
    identity = backend.cache_identity()
    assert secret not in identity
    assert len(identity) == 16


def test_cache_identity_deterministic() -> None:
    """같은 input → 같은 identity (cache key 안정성)."""
    a1 = OpenRouterAIBackend(api_key="same-key").cache_identity()
    a2 = OpenRouterAIBackend(api_key="same-key").cache_identity()
    assert a1 == a2


def test_cache_identity_distinguishes_different_keys() -> None:
    a = OpenRouterAIBackend(api_key="key-a").cache_identity()
    b = OpenRouterAIBackend(api_key="key-b").cache_identity()
    assert a != b
