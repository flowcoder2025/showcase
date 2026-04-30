from typing import Any
from unittest.mock import MagicMock

import pytest

from core.messaging import discord as discord_mod


def test_send_calls_webhook_execute(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_dw = MagicMock()
    fake_dw.execute.return_value = MagicMock(status_code=204)

    def fake_webhook(**k: Any) -> MagicMock:
        return fake_dw

    monkeypatch.setattr(discord_mod, "DiscordWebhook", fake_webhook)
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/x/y")

    result = discord_mod.send("테스트 메시지")
    assert result["status"] == 204
    fake_dw.execute.assert_called_once()


def test_send_raises_when_url_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    with pytest.raises(RuntimeError, match="DISCORD_WEBHOOK_URL"):
        discord_mod.send("hi")


def test_send_with_levels_uses_color(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class FakeWebhook:
        def __init__(self, **kwargs: object) -> None:
            captured["kwargs"] = kwargs

        def add_embed(self, embed: object) -> None:
            captured["embed"] = embed

        def execute(self) -> MagicMock:
            return MagicMock(status_code=204)

    def fake_embed(**k: Any) -> dict[str, Any]:
        return dict(k)

    monkeypatch.setattr(discord_mod, "DiscordWebhook", FakeWebhook)
    monkeypatch.setattr(discord_mod, "DiscordEmbed", fake_embed)
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/x/y")

    discord_mod.send("경고", level="warning", title="단가 이상치")
    assert captured["embed"]["color"] == discord_mod.LEVEL_COLORS["warning"]
