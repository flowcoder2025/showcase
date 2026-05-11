"""T36 — Backend audit log contract (R1-H1 + R3-N1).

각 backend가 demo_logger 또는 직접 print/stderr로 secret을 노출하지 않음을 검증.
sentinel을 init args로 주입한 후 1차 메서드 호출 시 caplog/capsys/stderr에
sentinel 흔적이 없어야 한다. DEMO_SAFE=1 mode로 외부 호출 차단.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import pytest
from flowcoder_office_tools.backends.discord import DiscordWebhookBackend
from flowcoder_office_tools.backends.gmail import GmailBackend
from flowcoder_office_tools.backends.mlx import MLXOCRBackend
from flowcoder_office_tools.backends.openrouter import OpenRouterAIBackend

_OPENROUTER_SENTINEL = "sk-or-v1-FAKE-OR-AUDIT-LEAK-SENTINEL"
_DISCORD_SENTINEL_TOKEN = "DISCORD-WEBHOOK-AUDIT-LEAK-SENTINEL-FAKE"
_GMAIL_SENTINEL = "ya29.GMAIL-AUDIT-LEAK-SENTINEL-FAKE"
_MLX_SENTINEL = "MLX-OPTIONAL-API-KEY-AUDIT-LEAK-SENTINEL-FAKE"


@pytest.mark.parametrize(
    "backend_factory,sentinel",
    [
        pytest.param(
            lambda: OpenRouterAIBackend(api_key=_OPENROUTER_SENTINEL),
            _OPENROUTER_SENTINEL,
            id="openrouter",
        ),
        pytest.param(
            lambda: DiscordWebhookBackend(
                webhook_url=f"https://discord.com/api/webhooks/x/{_DISCORD_SENTINEL_TOKEN}"
            ),
            _DISCORD_SENTINEL_TOKEN,
            id="discord",
        ),
        pytest.param(
            lambda: GmailBackend(token=_GMAIL_SENTINEL),
            _GMAIL_SENTINEL,
            id="gmail",
        ),
        pytest.param(
            lambda: MLXOCRBackend(base_url="http://localhost:11437", api_key=_MLX_SENTINEL),
            _MLX_SENTINEL,
            id="mlx",
        ),
    ],
)
def test_backend_does_not_leak_secret_to_logs(
    backend_factory: Callable[[], Any],
    sentinel: str,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEMO_SAFE", "1")
    caplog.set_level(logging.DEBUG)
    backend = backend_factory()

    method: Any = (
        getattr(backend, "extract", None)
        or getattr(backend, "chat", None)
        or getattr(backend, "send_discord", None)
        or getattr(backend, "send_email", None)
    )
    assert method is not None, f"no backend method found on {type(backend).__name__}"

    try:
        method("test")
    except Exception:
        pass

    captured = capsys.readouterr()
    assert sentinel not in caplog.text, f"caplog leak in {type(backend).__name__}"
    assert sentinel not in captured.out, f"stdout leak in {type(backend).__name__}"
    assert sentinel not in captured.err, f"stderr leak in {type(backend).__name__}"


def test_repr_does_not_leak_openrouter_key() -> None:
    """repr() 우발 호출 시 secret 노출 안 함."""
    backend = OpenRouterAIBackend(api_key=_OPENROUTER_SENTINEL)
    assert _OPENROUTER_SENTINEL not in repr(backend)


def test_repr_does_not_leak_discord_token() -> None:
    backend = DiscordWebhookBackend(
        webhook_url=f"https://discord.com/api/webhooks/x/{_DISCORD_SENTINEL_TOKEN}"
    )
    assert _DISCORD_SENTINEL_TOKEN not in repr(backend)


def test_repr_does_not_leak_gmail_token() -> None:
    backend = GmailBackend(token=_GMAIL_SENTINEL)
    assert _GMAIL_SENTINEL not in repr(backend)


def test_repr_does_not_leak_mlx_api_key() -> None:
    backend = MLXOCRBackend(base_url="http://localhost:11437", api_key=_MLX_SENTINEL)
    assert _MLX_SENTINEL not in repr(backend)
