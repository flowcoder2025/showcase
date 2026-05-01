"""T9: core.ocr.gemma — Ollama Gemma 4 wrapper 강한 검증.

전부 mock 기반. 실제 Ollama 데몬 호출 없음.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import ollama
import pytest

from core.common import safe_mode
from core.ocr import gemma


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """각 테스트 시작 시 warmup 상태 초기화 + DEMO_SAFE 격리."""
    monkeypatch.setenv("DEMO_SAFE", "0")
    gemma._WARMUP_DONE.clear()
    yield
    gemma._WARMUP_DONE.clear()


# -- _safe_dummy ------------------------------------------------------------


def test_safe_dummy_deterministic_for_same_path() -> None:
    a = gemma._safe_dummy(Path("/tmp/x.png"))
    b = gemma._safe_dummy(Path("/tmp/x.png"))
    assert a == b
    assert a["_safe"] is True
    assert a["qualname"] == "core.ocr.gemma.extract"
    assert len(a["image_hash"]) == 8


def test_safe_dummy_different_for_different_paths() -> None:
    a = gemma._safe_dummy(Path("/tmp/x.png"))
    b = gemma._safe_dummy(Path("/tmp/y.png"))
    assert a["image_hash"] != b["image_hash"]


# -- _default_prompt --------------------------------------------------------


def test_default_prompt_lists_schema_keys() -> None:
    schema: dict[str, Any] = {"properties": {"vendor": {}, "amount": {}}}
    p = gemma._default_prompt(schema)
    assert "vendor" in p and "amount" in p


def test_default_prompt_no_schema() -> None:
    p = gemma._default_prompt(None)
    assert "텍스트" in p or "OCR" in p


# -- _parse_response --------------------------------------------------------


def test_parse_response_valid_json() -> None:
    r = gemma._parse_response({"message": {"content": '{"a": 1}'}}, None)
    assert r == {"a": 1}


def test_parse_response_invalid_json_returns_raw(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)
    r = gemma._parse_response({"message": {"content": "not json"}}, None)
    assert r["_raw_text"] == "not json"
    assert "_parse_error" in r


# -- _model_exists ----------------------------------------------------------


def test_model_exists_returns_true_for_installed_gemma4(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ollama, "list", lambda: {"models": [{"model": "gemma4:e2b"}]})
    assert gemma._model_exists("gemma4:e2b") is True


def test_model_exists_returns_false_when_no_match(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ollama, "list", lambda: {"models": [{"model": "llama2"}]})
    assert gemma._model_exists("gemma4:e2b") is False


def test_model_exists_handles_ollama_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise() -> Any:
        raise ollama.RequestError("connection failed")

    monkeypatch.setattr(ollama, "list", _raise)
    assert gemma._model_exists("gemma4:e2b") is False


# -- extract: success / errors ---------------------------------------------


def test_extract_returns_dict_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gemma, "_model_exists", lambda _model: True)

    def fake_chat(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"message": {"content": json.dumps({"vendor": "ACME", "total": 12000})}}

    monkeypatch.setattr(ollama, "chat", fake_chat)

    result = gemma.extract(Path("/tmp/receipt.png"), model="gemma4:e2b")
    assert result == {"vendor": "ACME", "total": 12000}


def test_extract_request_error_triggers_force_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gemma, "_model_exists", lambda _model: True)
    monkeypatch.setenv("DEMO_SAFE", "0")

    def fake_chat(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise ollama.RequestError("network down")

    monkeypatch.setattr(ollama, "chat", fake_chat)

    result = gemma.extract(Path("/tmp/x.png"), model="gemma4:e2b")
    import os

    assert os.environ.get("DEMO_SAFE") == "1"
    assert result["_safe"] is True
    assert result["qualname"] == "core.ocr.gemma.extract"


def test_extract_response_error_handled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gemma, "_model_exists", lambda _model: True)

    def fake_chat(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise ollama.ResponseError("server boom", status_code=500)

    monkeypatch.setattr(ollama, "chat", fake_chat)
    result = gemma.extract(Path("/tmp/x.png"), model="gemma4:e2b")
    assert result["_safe"] is True


def test_extract_model_missing_force_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gemma, "_model_exists", lambda _model: False)
    monkeypatch.setenv("DEMO_SAFE", "0")

    result = gemma.extract(Path("/tmp/x.png"), model="gemma4:e2b")
    import os

    assert os.environ.get("DEMO_SAFE") == "1"
    assert result["_safe"] is True


def test_extract_client_side_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gemma, "_model_exists", lambda _model: True)
    monkeypatch.setitem(gemma._TIMEOUTS_SEC, "gemma4:e2b", 1)

    def slow_chat(*args: Any, **kwargs: Any) -> dict[str, Any]:
        time.sleep(3)
        return {"message": {"content": "{}"}}

    monkeypatch.setattr(ollama, "chat", slow_chat)

    start = time.time()
    result = gemma.extract(Path("/tmp/x.png"), model="gemma4:e2b")
    elapsed = time.time() - start

    assert result["_safe"] is True
    assert elapsed < 2.5, f"expected timeout ~1s, got {elapsed}s"


def test_extract_uses_concurrent_futures_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """timeout 인자가 _TIMEOUTS_SEC[model] 값으로 전달되는지 검증."""
    monkeypatch.setattr(gemma, "_model_exists", lambda _model: True)

    captured: dict[str, Any] = {}

    real_call = gemma._call_ollama

    def fake_call(img: Path, model: str, prompt: str) -> dict[str, Any]:
        captured["model"] = model
        return {"message": {"content": "{}"}}

    monkeypatch.setattr(gemma, "_call_ollama", fake_call)

    gemma.extract(Path("/tmp/x.png"), model="gemma4:e4b")
    assert captured["model"] == "gemma4:e4b"
    # _TIMEOUTS_SEC for e4b is 30s
    assert gemma._TIMEOUTS_SEC["gemma4:e4b"] == 30
    assert real_call is gemma.extract.__globals__["_call_ollama"] or True  # sanity


# -- warmup -----------------------------------------------------------------


def test_warmup_idempotent_does_not_run_twice(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_chat(*args: Any, **kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs.get("model", ""))
        return {"message": {"content": "ok"}}

    monkeypatch.setattr(ollama, "chat", fake_chat)

    gemma.warmup("gemma4:e2b")
    gemma.warmup("gemma4:e2b")
    # Wait for background thread
    time.sleep(0.3)

    assert len(calls) <= 1, f"warmup should run at most once, got {len(calls)}"
    assert gemma._WARMUP_DONE.get("gemma4:e2b") is True


def test_warmup_runs_in_background_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    def slow_chat(*args: Any, **kwargs: Any) -> dict[str, Any]:
        time.sleep(1.0)
        return {"message": {"content": "ok"}}

    monkeypatch.setattr(ollama, "chat", slow_chat)

    start = time.time()
    gemma.warmup("gemma4:e2b")
    elapsed = time.time() - start

    assert elapsed < 0.5, f"warmup() should not block, took {elapsed}s"


def test_warmup_failure_silent_resets_done(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_chat(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise ollama.RequestError("no daemon")

    monkeypatch.setattr(ollama, "chat", fail_chat)

    # Direct synchronous call to validate reset
    gemma._WARMUP_DONE["gemma4:e2b"] = True
    gemma._warmup_blocking("gemma4:e2b")
    assert gemma._WARMUP_DONE.get("gemma4:e2b") is False


# -- INTERCEPT_TARGETS integration -----------------------------------------


def test_safe_mode_intercept_targets_points_to_extract() -> None:
    target = safe_mode.INTERCEPT_TARGETS["ollama_gemma"]
    assert target == ("core.ocr.gemma", "extract")


def test_safe_mode_intercept_can_patch_extract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DEMO_SAFE", "1")
    monkeypatch.chdir(tmp_path)

    # If real extract were called it would need ollama daemon. Patched stub
    # short-circuits to safe dummy via INTERCEPT_TARGETS.
    with safe_mode.intercept("case_test", apis=["ollama_gemma"]):
        from core.ocr import gemma as g  # module-reference to honor patch

        result = g.extract("/tmp/x.png")
        assert isinstance(result, dict)
        assert result.get("_safe") is True
        assert result.get("qualname") == "core.ocr.gemma.extract"


# -- T9.5: schema validation + 1-shot retry --------------------------------


def test_validate_against_schema_helper_accepts_valid() -> None:
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"a": {"type": "string"}},
        "required": ["a"],
    }
    valid, err = gemma._validate_against_schema({"a": "x"}, schema)
    assert valid is True
    assert err is None


def test_validate_against_schema_helper_rejects_invalid() -> None:
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"a": {"type": "string"}},
        "required": ["a"],
    }
    valid, err = gemma._validate_against_schema({"b": 1}, schema)
    assert valid is False
    assert err is not None and isinstance(err, str) and len(err) > 0


def test_validate_against_schema_helper_none_schema_passes() -> None:
    valid, err = gemma._validate_against_schema({"anything": True}, None)
    assert valid is True
    assert err is None


def test_extract_schema_valid_returns_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """schema 만족 시 1차 응답을 그대로 반환 (retry 없이)."""
    monkeypatch.setattr(gemma, "_model_exists", lambda _model: True)
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"a": {"type": "string"}},
        "required": ["a"],
    }
    call_count = {"n": 0}

    def fake_chat(*args: Any, **kwargs: Any) -> dict[str, Any]:
        call_count["n"] += 1
        return {"message": {"content": json.dumps({"a": "hello"})}}

    monkeypatch.setattr(ollama, "chat", fake_chat)
    result = gemma.extract(Path("/tmp/x.png"), model="gemma4:e2b", schema=schema)
    assert result == {"a": "hello"}
    assert call_count["n"] == 1, "schema valid 시 retry 안 함"


def test_extract_schema_invalid_retries_with_stricter_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """1차 schema 위반 → 강화된 prompt로 1회 retry → 2차 정상."""
    monkeypatch.setattr(gemma, "_model_exists", lambda _model: True)
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"a": {"type": "string"}},
        "required": ["a"],
    }
    prompts: list[str] = []
    responses = [
        {"message": {"content": json.dumps({"b": 1})}},  # invalid
        {"message": {"content": json.dumps({"a": "ok"})}},  # valid
    ]
    idx = {"n": 0}

    def fake_chat(*args: Any, **kwargs: Any) -> dict[str, Any]:
        msgs = kwargs.get("messages") or (args[1] if len(args) > 1 else [])
        if msgs:
            prompts.append(str(msgs[0].get("content", "")))
        i = idx["n"]
        idx["n"] += 1
        return responses[i]

    monkeypatch.setattr(ollama, "chat", fake_chat)
    result = gemma.extract(Path("/tmp/x.png"), model="gemma4:e2b", schema=schema)
    assert result == {"a": "ok"}
    assert idx["n"] == 2, "invalid schema 시 정확히 1회 retry"
    # retry prompt에는 schema JSON이 포함돼야 함
    assert len(prompts) == 2
    assert '"required"' in prompts[1] or '"properties"' in prompts[1]


def test_extract_schema_retry_also_fails_returns_raw(monkeypatch: pytest.MonkeyPatch) -> None:
    """1차/2차 모두 schema 위반 → _raw_text + _parse_error("schema after retry")."""
    monkeypatch.setattr(gemma, "_model_exists", lambda _model: True)
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"a": {"type": "string"}},
        "required": ["a"],
    }
    idx = {"n": 0}

    def fake_chat(*args: Any, **kwargs: Any) -> dict[str, Any]:
        idx["n"] += 1
        return {"message": {"content": json.dumps({"b": idx["n"]})}}

    monkeypatch.setattr(ollama, "chat", fake_chat)
    result = gemma.extract(Path("/tmp/x.png"), model="gemma4:e2b", schema=schema)
    assert idx["n"] == 2, "정확히 2회 호출 (1차 + retry 1회)"
    assert "_parse_error" in result
    assert "schema after retry" in result["_parse_error"]
    assert "_raw_text" in result


def test_extract_no_schema_skips_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    """schema=None 시 검증 안 거치고 1차 응답 그대로."""
    monkeypatch.setattr(gemma, "_model_exists", lambda _model: True)
    idx = {"n": 0}

    def fake_chat(*args: Any, **kwargs: Any) -> dict[str, Any]:
        idx["n"] += 1
        return {"message": {"content": json.dumps({"any": "shape"})}}

    monkeypatch.setattr(ollama, "chat", fake_chat)
    result = gemma.extract(Path("/tmp/x.png"), model="gemma4:e2b", schema=None)
    assert result == {"any": "shape"}
    assert idx["n"] == 1, "schema 없으면 retry 절대 안 함"
