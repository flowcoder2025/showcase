from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from core.messaging import discord as discord_mod
from core.messaging.discord import OverdueLevelLiteral


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


def test_send_with_level_dispatches_to_send(monkeypatch: pytest.MonkeyPatch) -> None:
    """send_with_level은 내부적으로 send()를 호출해 단일 patch point를 보존한다."""
    captured: dict[str, Any] = {}

    def fake_send(
        content: str,
        *,
        level: str = "info",
        title: str | None = None,
        webhook_url: str | None = None,
    ) -> discord_mod.SendResult:
        captured["content"] = content
        captured["level"] = level
        captured["title"] = title
        captured["webhook_url"] = webhook_url
        captured["call_count"] = captured.get("call_count", 0) + 1
        return {"status": 204}

    monkeypatch.setattr(discord_mod, "send", fake_send)

    result = discord_mod.send_with_level(
        webhook_url="https://discord.com/api/webhooks/x/y",
        title="미수금 31일 경과",
        body="A사 결제 지연",
        level="strict",
    )

    assert result["status"] == 204
    assert captured["call_count"] == 1
    assert captured["content"] == "A사 결제 지연"
    assert captured["title"] == "미수금 31일 경과"
    assert captured["level"] == "danger"
    assert captured["webhook_url"] == "https://discord.com/api/webhooks/x/y"


def test_send_with_level_color_per_level() -> None:
    """4단계 도메인 level → internal level → LEVEL_COLORS 색상 lookup."""
    expected = {
        "friendly": ("info", "3498db"),  # blue
        "neutral": ("warning", "f39c12"),  # orange
        "strict": ("danger", "e74c3c"),  # red
        "final": ("critical", "000000"),  # black
    }
    for domain_level, (internal, color_hex) in expected.items():
        assert discord_mod.OVERDUE_LEVEL_TO_INTERNAL[domain_level] == internal
        assert discord_mod.LEVEL_COLORS[internal] == color_hex


def test_send_with_level_unknown_level_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Literal 우회로 잘못된 문자열을 전달하면 KeyError."""

    def fake_send(*args: Any, **kwargs: Any) -> discord_mod.SendResult:
        raise AssertionError("send must not be called for invalid levels")

    monkeypatch.setattr(discord_mod, "send", fake_send)

    with pytest.raises(KeyError, match="unknown overdue level"):
        discord_mod.send_with_level(
            webhook_url="https://discord.com/api/webhooks/x/y",
            title="t",
            body="b",
            level=cast(OverdueLevelLiteral, "unknown"),
        )


def test_send_with_level_uses_critical_for_final_60plus(monkeypatch: pytest.MonkeyPatch) -> None:
    """final 단계는 critical(검정)로 매핑되어야 한다."""
    captured: dict[str, Any] = {}

    def fake_send(
        content: str,
        *,
        level: str = "info",
        title: str | None = None,
        webhook_url: str | None = None,
    ) -> discord_mod.SendResult:
        captured["level"] = level
        return {"status": 204}

    monkeypatch.setattr(discord_mod, "send", fake_send)

    discord_mod.send_with_level(
        webhook_url="https://discord.com/api/webhooks/x/y",
        title="60일 초과 — 법무 escalation",
        body="B사 미수금 90일",
        level="final",
    )

    assert captured["level"] == "critical"
    assert discord_mod.LEVEL_COLORS["critical"] == "000000"
