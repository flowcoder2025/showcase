from unittest.mock import MagicMock, patch
from core.messaging import discord as discord_mod


def test_send_calls_webhook_execute(monkeypatch):
    fake_dw = MagicMock()
    fake_dw.execute.return_value = MagicMock(status_code=204)

    monkeypatch.setattr(discord_mod, "DiscordWebhook", lambda **k: fake_dw)
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/x/y")

    result = discord_mod.send("테스트 메시지")
    assert result["status"] == 204
    fake_dw.execute.assert_called_once()


def test_send_raises_when_url_missing(monkeypatch):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    import pytest
    with pytest.raises(RuntimeError, match="DISCORD_WEBHOOK_URL"):
        discord_mod.send("hi")


def test_send_with_levels_uses_color(monkeypatch):
    captured = {}

    class FakeWebhook:
        def __init__(self, **kwargs):
            captured["kwargs"] = kwargs
        def add_embed(self, embed):
            captured["embed"] = embed
        def execute(self):
            return MagicMock(status_code=204)

    monkeypatch.setattr(discord_mod, "DiscordWebhook", FakeWebhook)
    monkeypatch.setattr(discord_mod, "DiscordEmbed", lambda **k: dict(k))
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/x/y")

    discord_mod.send("경고", level="warning", title="단가 이상치")
    assert captured["embed"]["color"] == discord_mod.LEVEL_COLORS["warning"]
