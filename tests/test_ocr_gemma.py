"""core.ocr.gemma — MLX (mlx_vlm.server OpenAI-compat) wrapper 강한 검증.

전부 mock 기반. 실제 mlx_vlm.server 호출 없음.
INTERCEPT_TARGETS["ollama_gemma"] 키 이름은 외부 계약이라 그대로 유지.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    RateLimitError,
)

from core.common import safe_mode
from core.ocr import _mlx_server, gemma


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    """각 테스트 시작 시 warmup 상태 초기화 + DEMO_SAFE 격리 + ensure_running mock."""
    monkeypatch.setenv("DEMO_SAFE", "0")
    gemma._WARMUP_DONE.clear()
    # ensure_running은 외부 프로세스를 띄우므로 모든 OCR 테스트에서 noop 처리.
    monkeypatch.setattr(_mlx_server, "ensure_running", lambda *a, **k: None)
    yield
    gemma._WARMUP_DONE.clear()


def _fake_chat_response(content: str) -> SimpleNamespace:
    """openai SDK가 반환하는 ChatCompletion 객체의 최소 shape."""
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def _patch_openai(monkeypatch: pytest.MonkeyPatch, content: str) -> dict[str, Any]:
    """``OpenAI(...).chat.completions.create``를 고정 응답으로 mock."""
    captured: dict[str, Any] = {}

    def fake_create(**kwargs: Any) -> SimpleNamespace:
        captured["kwargs"] = kwargs
        return _fake_chat_response(content)

    fake_client = MagicMock()
    fake_client.chat.completions.create = fake_create
    monkeypatch.setattr(gemma, "_client", lambda _alias: fake_client)
    return captured


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


def test_default_prompt_forbids_code_fence() -> None:
    """mlx_vlm은 response_format json 미지원 → 프롬프트로 fence 차단."""
    schema: dict[str, Any] = {"properties": {"a": {}}}
    p = gemma._default_prompt(schema)
    assert "코드펜스" in p or "```" in p


# -- _strip_code_fence ------------------------------------------------------


def test_strip_code_fence_handles_json_fence() -> None:
    assert gemma._strip_code_fence('```json\n{"a": 1}\n```') == '{"a": 1}'


def test_strip_code_fence_handles_plain_fence() -> None:
    assert gemma._strip_code_fence('```\n{"a": 1}\n```') == '{"a": 1}'


def test_strip_code_fence_returns_unchanged_when_no_fence() -> None:
    assert gemma._strip_code_fence('{"a": 1}') == '{"a": 1}'


def test_strip_code_fence_strips_leading_trailing_whitespace() -> None:
    assert gemma._strip_code_fence('  \n```json\n{"a":1}\n```\n  ') == '{"a":1}'


# -- _to_data_url -----------------------------------------------------------


def test_to_data_url_png(tmp_path: Path) -> None:
    p = tmp_path / "x.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    url = gemma._to_data_url(p)
    assert url.startswith("data:image/png;base64,")


def test_to_data_url_jpeg(tmp_path: Path) -> None:
    p = tmp_path / "x.jpg"
    p.write_bytes(b"\xff\xd8\xff\xe0fake")
    url = gemma._to_data_url(p)
    assert url.startswith("data:image/jpeg;base64,") or url.startswith("data:image/jpg;base64,")


def test_to_data_url_unknown_ext_defaults_to_png(tmp_path: Path) -> None:
    p = tmp_path / "x.unknownext"
    p.write_bytes(b"raw")
    url = gemma._to_data_url(p)
    assert url.startswith("data:image/png;base64,")


# -- _parse_response --------------------------------------------------------


def test_parse_response_valid_json() -> None:
    r = gemma._parse_response({"message": {"content": '{"a": 1}'}}, None)
    assert r == {"a": 1}


def test_parse_response_strips_fence_before_parse() -> None:
    r = gemma._parse_response({"message": {"content": '```json\n{"a": 1}\n```'}}, None)
    assert r == {"a": 1}


def test_parse_response_invalid_json_returns_raw(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)
    r = gemma._parse_response({"message": {"content": "not json"}}, None)
    assert r["_raw_text"] == "not json"
    assert "_parse_error" in r


# -- extract: success / errors ---------------------------------------------


def test_extract_returns_dict_on_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    img = tmp_path / "receipt.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    _patch_openai(monkeypatch, json.dumps({"vendor": "ACME", "total": 12000}))

    result = gemma.extract(img, model="gemma4:e2b")
    assert result == {"vendor": "ACME", "total": 12000}


def test_extract_sends_vision_content_array(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """OpenAI 표준 vision content array 형식으로 호출되는지 검증."""
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    captured = _patch_openai(monkeypatch, "{}")

    gemma.extract(img, model="gemma4:e2b")
    msgs = captured["kwargs"]["messages"]
    assert msgs[0]["role"] == "user"
    content = msgs[0]["content"]
    types = [item["type"] for item in content]
    assert "text" in types
    assert "image_url" in types
    image_item = next(c for c in content if c["type"] == "image_url")
    assert image_item["image_url"]["url"].startswith("data:image/")


def test_extract_passes_model_path_not_alias(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """mlx_vlm.server는 model field에 디렉토리 경로를 받는다."""
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    captured = _patch_openai(monkeypatch, "{}")

    gemma.extract(img, model="gemma4:e2b")
    model_arg = captured["kwargs"]["model"]
    assert "gemma-4-e2b-mlx" in model_arg, "model path가 e2b 디렉토리여야 함"


def test_extract_e4b_uses_e4b_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    captured = _patch_openai(monkeypatch, "{}")

    gemma.extract(img, model="gemma4:e4b")
    assert "gemma-4-e4b-mlx" in captured["kwargs"]["model"]


def test_extract_connection_error_triggers_force_safe(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    monkeypatch.setenv("DEMO_SAFE", "0")

    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = APIConnectionError(
        request=httpx.Request("POST", "http://x")
    )
    monkeypatch.setattr(gemma, "_client", lambda _alias: fake_client)

    result = gemma.extract(img, model="gemma4:e2b")
    import os

    assert os.environ.get("DEMO_SAFE") == "1"
    assert result["_safe"] is True
    assert result["qualname"] == "core.ocr.gemma.extract"


def test_extract_timeout_error_handled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")

    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = APITimeoutError(
        request=httpx.Request("POST", "http://x")
    )
    monkeypatch.setattr(gemma, "_client", lambda _alias: fake_client)

    result = gemma.extract(img, model="gemma4:e2b")
    assert result["_safe"] is True


def test_extract_rate_limit_error_handled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")

    fake_resp = httpx.Response(status_code=429, request=httpx.Request("POST", "http://x"))
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = RateLimitError(
        message="rate limit", response=fake_resp, body=None
    )
    monkeypatch.setattr(gemma, "_client", lambda _alias: fake_client)

    result = gemma.extract(img, model="gemma4:e2b")
    assert result["_safe"] is True


def test_extract_status_error_handled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")

    fake_resp = httpx.Response(status_code=500, request=httpx.Request("POST", "http://x"))
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = APIStatusError(
        message="server boom", response=fake_resp, body=None
    )
    monkeypatch.setattr(gemma, "_client", lambda _alias: fake_client)

    result = gemma.extract(img, model="gemma4:e2b")
    assert result["_safe"] is True


def test_extract_ensure_running_failure_force_safe(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """ensure_running이 binary/모델 부재로 실패 시 force_safe."""
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    monkeypatch.setenv("DEMO_SAFE", "0")

    def raise_not_found(*_a: Any, **_k: Any) -> None:
        raise FileNotFoundError("AX_MLX_BIN missing")

    monkeypatch.setattr(_mlx_server, "ensure_running", raise_not_found)
    result = gemma.extract(img, model="gemma4:e2b")
    import os

    assert os.environ.get("DEMO_SAFE") == "1"
    assert result["_safe"] is True


def test_extract_client_side_timeout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    monkeypatch.setitem(gemma._TIMEOUTS_SEC, "gemma4:e2b", 1)

    def slow_create(**kwargs: Any) -> SimpleNamespace:
        time.sleep(3)
        return _fake_chat_response("{}")

    fake_client = MagicMock()
    fake_client.chat.completions.create = slow_create
    monkeypatch.setattr(gemma, "_client", lambda _alias: fake_client)

    start = time.time()
    result = gemma.extract(img, model="gemma4:e2b")
    elapsed = time.time() - start

    assert result["_safe"] is True
    assert elapsed < 2.5, f"expected timeout ~1s, got {elapsed}s"


# -- warmup -----------------------------------------------------------------


def test_warmup_idempotent_does_not_run_twice(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_ensure(alias: str, **_k: Any) -> None:
        calls.append(alias)

    monkeypatch.setattr(_mlx_server, "ensure_running", fake_ensure)

    gemma.warmup("gemma4:e2b")
    gemma.warmup("gemma4:e2b")
    time.sleep(0.3)

    assert len(calls) <= 1, f"warmup should run at most once, got {len(calls)}"
    assert gemma._WARMUP_DONE.get("gemma4:e2b") is True


def test_warmup_runs_in_background_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    def slow_ensure(*_a: Any, **_k: Any) -> None:
        time.sleep(1.0)

    monkeypatch.setattr(_mlx_server, "ensure_running", slow_ensure)

    start = time.time()
    gemma.warmup("gemma4:e2b")
    elapsed = time.time() - start

    assert elapsed < 0.5, f"warmup() should not block, took {elapsed}s"


def test_warmup_failure_silent_resets_done(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_ensure(*_a: Any, **_k: Any) -> None:
        raise RuntimeError("no bin")

    monkeypatch.setattr(_mlx_server, "ensure_running", fail_ensure)

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

    with safe_mode.intercept("case_test", apis=["ollama_gemma"]):
        from core.ocr import gemma as g

        result = g.extract("/tmp/x.png")
        assert isinstance(result, dict)
        assert result.get("_safe") is True
        assert result.get("qualname") == "core.ocr.gemma.extract"


# -- schema validation + 1-shot retry --------------------------------------


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


def test_extract_schema_valid_returns_response(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """schema 만족 시 1차 응답을 그대로 반환 (retry 없이)."""
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"a": {"type": "string"}},
        "required": ["a"],
    }
    call_count = {"n": 0}

    def fake_create(**kwargs: Any) -> SimpleNamespace:
        call_count["n"] += 1
        return _fake_chat_response(json.dumps({"a": "hello"}))

    fake_client = MagicMock()
    fake_client.chat.completions.create = fake_create
    monkeypatch.setattr(gemma, "_client", lambda _alias: fake_client)

    result = gemma.extract(img, model="gemma4:e2b", schema=schema)
    assert result == {"a": "hello"}
    assert call_count["n"] == 1, "schema valid 시 retry 안 함"


def test_extract_schema_invalid_retries_with_stricter_prompt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """1차 schema 위반 → 강화된 prompt로 1회 retry → 2차 정상."""
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"a": {"type": "string"}},
        "required": ["a"],
    }
    prompts: list[str] = []
    responses = [
        _fake_chat_response(json.dumps({"b": 1})),  # invalid
        _fake_chat_response(json.dumps({"a": "ok"})),  # valid
    ]
    idx = {"n": 0}

    def fake_create(**kwargs: Any) -> SimpleNamespace:
        msgs = kwargs.get("messages") or []
        if msgs:
            content = msgs[0]["content"]
            if isinstance(content, list):
                # extract text part
                for item in content:
                    if item.get("type") == "text":
                        prompts.append(item["text"])
                        break
            else:
                prompts.append(str(content))
        i = idx["n"]
        idx["n"] += 1
        return responses[i]

    fake_client = MagicMock()
    fake_client.chat.completions.create = fake_create
    monkeypatch.setattr(gemma, "_client", lambda _alias: fake_client)

    result = gemma.extract(img, model="gemma4:e2b", schema=schema)
    assert result == {"a": "ok"}
    assert idx["n"] == 2, "invalid schema 시 정확히 1회 retry"
    assert len(prompts) == 2
    assert '"required"' in prompts[1] or '"properties"' in prompts[1]


def test_extract_schema_retry_also_fails_returns_raw(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """1차/2차 모두 schema 위반 → _raw_text + _parse_error("schema after retry")."""
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"a": {"type": "string"}},
        "required": ["a"],
    }
    idx = {"n": 0}

    def fake_create(**kwargs: Any) -> SimpleNamespace:
        idx["n"] += 1
        return _fake_chat_response(json.dumps({"b": idx["n"]}))

    fake_client = MagicMock()
    fake_client.chat.completions.create = fake_create
    monkeypatch.setattr(gemma, "_client", lambda _alias: fake_client)

    result = gemma.extract(img, model="gemma4:e2b", schema=schema)
    assert idx["n"] == 2, "정확히 2회 호출 (1차 + retry 1회)"
    assert "_parse_error" in result
    assert "schema after retry" in result["_parse_error"]
    assert "_raw_text" in result


def test_extract_no_schema_skips_validation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """schema=None 시 검증 안 거치고 1차 응답 그대로."""
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    idx = {"n": 0}

    def fake_create(**kwargs: Any) -> SimpleNamespace:
        idx["n"] += 1
        return _fake_chat_response(json.dumps({"any": "shape"}))

    fake_client = MagicMock()
    fake_client.chat.completions.create = fake_create
    monkeypatch.setattr(gemma, "_client", lambda _alias: fake_client)

    result = gemma.extract(img, model="gemma4:e2b", schema=None)
    assert result == {"any": "shape"}
    assert idx["n"] == 1, "schema 없으면 retry 절대 안 함"
