from typing import Any
from unittest.mock import MagicMock

import pytest

from core.ai import client


def test_chat_returns_text_on_first_model_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content="hello"))]

    class FakeOpenAI:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        class chat:
            class completions:
                @staticmethod
                def create(**kwargs: Any) -> Any:
                    return fake_response

    monkeypatch.setattr(client, "OpenAI", FakeOpenAI)
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake")

    result = client.chat([{"role": "user", "content": "hi"}])
    assert result == "hello"


def test_chat_falls_back_when_primary_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_call(model: str, messages: list[dict[str, Any]], **k: Any) -> str:
        calls.append(model)
        if model == client.MODEL_PRIORITY[0]:
            raise client.RateLimitError("429")
        return "fallback ok"

    monkeypatch.setattr(client, "_call", fake_call)
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake")

    result = client.chat([{"role": "user", "content": "hi"}])
    assert result == "fallback ok"
    assert calls == [client.MODEL_PRIORITY[0], client.MODEL_PRIORITY[1]]


def test_chat_force_safe_when_all_models_fail(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake_call(model: str, messages: list[dict[str, Any]], **k: Any) -> str:
        raise client.ServerError("500")

    monkeypatch.setattr(client, "_call", fake_call)
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake")
    monkeypatch.setenv("DEMO_SAFE", "0")

    result = client.chat([{"role": "user", "content": "hi"}])
    assert "_safe" in str(result) or "safe" in str(result).lower() or result == "[SAFE-FALLBACK]"
    assert "AUTO-SAFE" in capsys.readouterr().out


def test_model_priority_is_immutable() -> None:
    """MODEL_PRIORITY should be a tuple to prevent global mutation."""
    assert isinstance(client.MODEL_PRIORITY, tuple)
    # immutability check: tuple has no append method
    assert not hasattr(client.MODEL_PRIORITY, "append")


def test_chat_short_circuits_under_safe_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """DEMO_SAFE=1 → chat() returns [SAFE-FALLBACK] without network call."""
    monkeypatch.setenv("DEMO_SAFE", "1")

    # Verify network is not called: replace _call with a sentinel
    def _should_not_call(*args: Any, **kwargs: Any) -> str:
        raise AssertionError("safe mode must short-circuit before network call")

    monkeypatch.setattr(client, "_call", _should_not_call)

    result = client.chat([{"role": "user", "content": "hi"}])
    assert result == "[SAFE-FALLBACK]"
