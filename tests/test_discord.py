import io
from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from rich.console import Console

from core.messaging import discord as discord_mod
from core.messaging.discord import OverdueLevelLiteral

SECRET_WEBHOOK = "https://discord.com/api/webhooks/123456789/abcdefSECRETTOKEN"


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


# ---------------------------------------------------------------------------
# T1.5 fixer additions
# ---------------------------------------------------------------------------


def test_send_warns_on_429_status(monkeypatch: pytest.MonkeyPatch) -> None:
    """429 (rate limit) 응답 시 demo_logger.warning 호출 — raise 아님."""
    fake_dw = MagicMock()
    fake_dw.execute.return_value = MagicMock(status_code=429)

    def fake_webhook(**k: Any) -> MagicMock:
        return fake_dw

    monkeypatch.setattr(discord_mod, "DiscordWebhook", fake_webhook)
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", SECRET_WEBHOOK)

    warnings: list[str] = []

    class FakeLogger:
        def info(self, msg: str) -> None: ...
        def success(self, msg: str) -> None: ...
        def warning(self, msg: str) -> None:
            warnings.append(msg)

        def error(self, msg: str) -> None: ...

    monkeypatch.setattr(discord_mod, "demo_logger", lambda case_id: FakeLogger())

    result = discord_mod.send("hi")
    assert result["status"] == 429
    assert len(warnings) == 1
    assert "429" in warnings[0]


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_send_warns_on_5xx_status(monkeypatch: pytest.MonkeyPatch, status: int) -> None:
    fake_dw = MagicMock()
    fake_dw.execute.return_value = MagicMock(status_code=status)

    def fake_webhook(**k: Any) -> MagicMock:
        return fake_dw

    monkeypatch.setattr(discord_mod, "DiscordWebhook", fake_webhook)
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", SECRET_WEBHOOK)

    warnings: list[str] = []

    class FakeLogger:
        def info(self, msg: str) -> None: ...
        def success(self, msg: str) -> None: ...
        def warning(self, msg: str) -> None:
            warnings.append(msg)

        def error(self, msg: str) -> None: ...

    monkeypatch.setattr(discord_mod, "demo_logger", lambda case_id: FakeLogger())

    discord_mod.send("hi")
    assert len(warnings) == 1
    assert str(status) in warnings[0]


def test_send_does_not_warn_on_2xx(monkeypatch: pytest.MonkeyPatch) -> None:
    """정상(204) 응답에는 warning 발생 없음."""
    fake_dw = MagicMock()
    fake_dw.execute.return_value = MagicMock(status_code=204)

    def fake_webhook(**k: Any) -> MagicMock:
        return fake_dw

    monkeypatch.setattr(discord_mod, "DiscordWebhook", fake_webhook)
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", SECRET_WEBHOOK)

    warnings: list[str] = []

    class FakeLogger:
        def info(self, msg: str) -> None: ...
        def success(self, msg: str) -> None: ...
        def warning(self, msg: str) -> None:
            warnings.append(msg)

        def error(self, msg: str) -> None: ...

    monkeypatch.setattr(discord_mod, "demo_logger", lambda case_id: FakeLogger())

    discord_mod.send("hi")
    assert warnings == []


def test_send_warning_does_not_leak_webhook_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """warning 경로에서 demo_logger를 거치므로 webhook URL은 secrets_mask에 의해 마스킹된다."""
    fake_dw = MagicMock()
    fake_dw.execute.return_value = MagicMock(status_code=429)

    def fake_webhook(**k: Any) -> MagicMock:
        return fake_dw

    monkeypatch.setattr(discord_mod, "DiscordWebhook", fake_webhook)
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", SECRET_WEBHOOK)

    # 실제 demo_logger를 사용하되 console 출력만 캡처해 secrets_mask 적용 여부를 검증.
    buf = io.StringIO()

    class CapturingLogger:
        def __init__(self, case_id: str) -> None:
            from core.common.demo_logger import DemoLogger

            self._inner = DemoLogger(case_id)
            self._inner.console = Console(file=buf, force_terminal=False, no_color=True)

        def info(self, msg: str) -> None:
            self._inner.info(msg)

        def success(self, msg: str) -> None:
            self._inner.success(msg)

        def warning(self, msg: str) -> None:
            self._inner.warning(msg)

        def error(self, msg: str) -> None:
            self._inner.error(msg)

    monkeypatch.setattr(discord_mod, "demo_logger", lambda case_id: CapturingLogger(case_id))

    discord_mod.send("hi")
    output = buf.getvalue()
    # webhook의 시크릿 토큰이 평문으로 노출되어선 안 됨.
    assert "abcdefSECRETTOKEN" not in output
    assert "123456789" not in output


@pytest.mark.parametrize("body", ["", "   ", "\n\t  ", "　"])
def test_send_with_level_empty_body_raises(monkeypatch: pytest.MonkeyPatch, body: str) -> None:
    """빈 또는 whitespace-only body는 ValueError로 거절한다."""

    def fake_send(*args: Any, **kwargs: Any) -> discord_mod.SendResult:
        raise AssertionError("send must not be called for empty body")

    monkeypatch.setattr(discord_mod, "send", fake_send)

    with pytest.raises(ValueError, match="body must not be empty"):
        discord_mod.send_with_level(
            webhook_url=SECRET_WEBHOOK,
            title="t",
            body=body,
            level="strict",
        )


def test_send_with_level_non_empty_body_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    """비어있지 않은 body는 정상 통과해야 한다 (regression 가드)."""
    captured: dict[str, Any] = {}

    def fake_send(
        content: str,
        *,
        level: str = "info",
        title: str | None = None,
        webhook_url: str | None = None,
    ) -> discord_mod.SendResult:
        captured["content"] = content
        return {"status": 204}

    monkeypatch.setattr(discord_mod, "send", fake_send)

    discord_mod.send_with_level(
        webhook_url=SECRET_WEBHOOK,
        title="t",
        body=" 실제 내용 ",
        level="friendly",
    )
    assert captured["content"] == " 실제 내용 "
