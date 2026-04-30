from unittest.mock import MagicMock

from core.ai import client


def test_chat_returns_text_on_first_model_success(monkeypatch):
    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content="hello"))]

    class FakeOpenAI:
        def __init__(self, *a, **k): pass
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    return fake_response

    monkeypatch.setattr(client, "OpenAI", FakeOpenAI)
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake")

    result = client.chat([{"role": "user", "content": "hi"}])
    assert result == "hello"


def test_chat_falls_back_when_primary_raises(monkeypatch):
    calls = []

    def fake_call(model, messages, **k):
        calls.append(model)
        if model == client.MODEL_PRIORITY[0]:
            raise client.RateLimitError("429")
        return "fallback ok"

    monkeypatch.setattr(client, "_call", fake_call)
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake")

    result = client.chat([{"role": "user", "content": "hi"}])
    assert result == "fallback ok"
    assert calls == [client.MODEL_PRIORITY[0], client.MODEL_PRIORITY[1]]


def test_chat_force_safe_when_all_models_fail(monkeypatch, capsys):
    def fake_call(model, messages, **k):
        raise client.ServerError("500")

    monkeypatch.setattr(client, "_call", fake_call)
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake")
    monkeypatch.setenv("DEMO_SAFE", "0")

    result = client.chat([{"role": "user", "content": "hi"}])
    assert "_safe" in str(result) or "safe" in str(result).lower() or result == "[SAFE-FALLBACK]"
    assert "AUTO-SAFE" in capsys.readouterr().out
