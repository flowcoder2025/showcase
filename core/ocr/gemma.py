"""MLX Gemma 4 wrapper — 영수증/세금계산서 OCR.

NOTE: 외부 호출은 모듈 참조로 호출 (safe_mode patch 격리):
    from core.ocr import gemma
    gemma.extract(...)

INTERCEPT_TARGETS["ollama_gemma"] = ("core.ocr.gemma", "extract") — 단일 patch point.
INTERCEPT_TARGETS 키 이름은 외부 계약(meta.yaml ``external_apis``)이라 그대로 유지.
내부 백엔드는 ollama → mlx_vlm.server (OpenAI 호환) 로 교체됐다.

Architecture
- ``warmup`` / ``_safe_dummy`` / ``_call_mlx`` / ``_parse_response`` 은 internal helper.
  외부에서 직접 호출하지 않는다 (safe_mode가 ``extract``만 patch).
- client-side timeout: ``concurrent.futures.ThreadPoolExecutor`` + ``future.result(timeout=...)``
  로 wall-clock timeout을 강제한다 (R3-O2). openai SDK 자체 timeout과 별개로 작동.
- 실패 시 모두 ``safe_mode.force_safe`` 호출 + ``_safe_dummy`` 반환 — 시연 흐름이
  깨지지 않게 한다.
- 백엔드 spawn/cleanup은 ``core.ocr._mlx_server``가 관리. ``extract`` 진입 시
  ``mlx_server.ensure_running``으로 idempotent 보장. ``runner.py`` 종료 시 atexit
  + signal handler로 process group 단위 회수.
"""

from __future__ import annotations

import base64
import concurrent.futures
import hashlib
import json
import mimetypes
import threading
from pathlib import Path
from typing import Any, Literal, cast

import jsonschema
from openai import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)

from core.common import safe_mode
from core.common.demo_logger import demo_logger
from core.ocr import _mlx_server

ModelLiteral = Literal["gemma4:e2b", "gemma4:e4b"]
_TIMEOUTS_SEC: dict[str, int] = {"gemma4:e2b": 30, "gemma4:e4b": 60}
_WARMUP_DONE: dict[str, bool] = {}
_WARMUP_LOCK = threading.Lock()
_MAX_OUTPUT_TOKENS: int = 2048


# -- public API -------------------------------------------------------------


def warmup(model: ModelLiteral = "gemma4:e2b") -> None:
    """백그라운드 thread로 mlx_vlm.server 기동 + 더미 추론 1회 — 콜드스타트 회피.

    runner.py 시작 시점에 호출. 이미 warmup 완료된 모델은 재실행 안 함
    (idempotent, lock 보호). 실패 시 ``_WARMUP_DONE[model]``을 False로 reset해
    재시도 가능하게 한다.
    """
    with _WARMUP_LOCK:
        if _WARMUP_DONE.get(model):
            return
        _WARMUP_DONE[model] = True  # 재호출 방지 우선 마킹

    threading.Thread(target=_warmup_blocking, args=(model,), daemon=True).start()


def extract(
    image_path: Path | str,
    *,
    model: ModelLiteral = "gemma4:e2b",
    schema: dict[str, Any] | None = None,
    prompt: str | None = None,
) -> dict[str, Any]:
    """이미지 OCR → 구조화 dict.

    Args:
        image_path: OCR 대상 이미지 경로.
        model: ``gemma4:e2b`` (default, 빠름) 또는 ``gemma4:e4b`` (정확).
        schema: JSON schema dict (``properties`` 키로 OCR 결과 구조 가이드).
        prompt: 사용자 지정 프롬프트 (없으면 ``_default_prompt`` 사용).

    Returns:
        성공: mlx 응답을 schema 가이드로 파싱한 dict.
        실패: ``{"_safe": True, "qualname": ..., "image_hash": ...}`` (safe_dummy).

    Failure modes (모두 force_safe + dummy 반환):
        - mlx_vlm.server 미기동 + spawn 실패 (binary/모델 경로 부재 등)
        - timeout (gemma4:e2b 30s, gemma4:e4b 60s — client-side concurrent.futures)
        - openai SDK 예외 (APIConnectionError / APITimeoutError / APIStatusError /
          RateLimitError / 일반 APIError)
    """
    img_path = Path(image_path)

    try:
        _mlx_server.ensure_running(model)
    except (FileNotFoundError, RuntimeError) as e:
        safe_mode.force_safe(f"mlx server unavailable: {type(e).__name__}: {e}")
        return _safe_dummy(img_path)

    timeout = _TIMEOUTS_SEC[model]
    user_prompt = prompt or _default_prompt(schema)

    parsed = _run_with_timeout(img_path, model, user_prompt, timeout, schema)
    if parsed is None:
        return _safe_dummy(img_path)

    # Schema validation + 1-shot retry — case07/08 OCR 정확도 직결.
    # parse 실패 응답(``_raw_text``)은 schema 검증을 건너뛴다 (이미 실패 채널).
    if schema is not None and "_raw_text" not in parsed:
        valid, err = _validate_against_schema(parsed, schema)
        if not valid:
            log = demo_logger("ocr.gemma")
            log.warning(f"schema validation failed: {err}; retrying with stricter prompt")
            stricter = (
                f"{user_prompt}\n\n"
                "이전 응답이 schema를 만족하지 못했습니다. 다음 JSON schema를 정확히 준수하세요:\n"
                f"{json.dumps(schema, ensure_ascii=False)}\n"
                "출력은 JSON만, 마크다운 코드펜스(```) 없이."
            )
            retry_parsed = _run_with_timeout(img_path, model, stricter, timeout, schema)
            if retry_parsed is None:
                return {
                    "_raw_text": json.dumps(parsed, ensure_ascii=False),
                    "_parse_error": f"schema validation: {err}",
                }
            if "_raw_text" in retry_parsed:
                return retry_parsed
            valid2, err2 = _validate_against_schema(retry_parsed, schema)
            if valid2:
                return retry_parsed
            return {
                "_raw_text": json.dumps(retry_parsed, ensure_ascii=False),
                "_parse_error": f"schema after retry: {err2}",
            }
    return parsed


def _run_with_timeout(
    img_path: Path,
    model: str,
    prompt: str,
    timeout: int,
    schema: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """mlx_vlm.server 1회 호출 + parse. 실패 시 ``None`` 반환 (caller가 ``_safe_dummy`` 결정).

    NOTE: ``ThreadPoolExecutor.__exit__``는 모든 worker 완료까지 block한다.
    timeout 시 즉시 반환해야 하므로 ``with`` 블록을 쓰지 않고 ``shutdown(wait=False)``로
    백그라운드 thread를 fire-and-forget 한다 (daemon-like). worker가 mlx
    호출에 갇혀도 메인 흐름은 차단되지 않는다.
    """
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = pool.submit(_call_mlx, img_path, model, prompt, timeout)
        try:
            response = future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            safe_mode.force_safe(f"gemma {model} timeout {timeout}s")
            return None
        except (
            APIConnectionError,
            APITimeoutError,
            RateLimitError,
            APIStatusError,
            APIError,
        ) as e:
            safe_mode.force_safe(f"gemma {model} failed: {type(e).__name__}: {e}")
            return None
        return _parse_response(response, schema)
    finally:
        pool.shutdown(wait=False)


def _validate_against_schema(
    data: dict[str, Any], schema: dict[str, Any] | None
) -> tuple[bool, str | None]:
    """``jsonschema.validate`` 래퍼. (valid, error_msg) 반환.

    schema가 ``None``이면 항상 통과. ``ValidationError`` 메시지는 1차 줄만 보존
    (장황한 stack info는 prompt에 포함시키기에 부적합).
    """
    if schema is None:
        return True, None
    try:
        jsonschema.validate(data, schema)
        return True, None
    except jsonschema.ValidationError as e:
        msg = (e.message or str(e)).split("\n")[0]
        return False, msg
    except jsonschema.SchemaError as e:
        return False, f"invalid schema: {e.message}"


# -- internal helpers -------------------------------------------------------


def _warmup_blocking(model: str) -> None:
    """동기 warmup. 실패는 silent (extract 호출 시 정식 처리)."""
    try:
        alias = cast(ModelLiteral, model)
        _mlx_server.ensure_running(alias)
        # /health가 통과하면 모델은 로딩 완료 상태. 별도 chat 호출 없이도 충분.
    except (FileNotFoundError, RuntimeError, OSError):
        with _WARMUP_LOCK:
            _WARMUP_DONE[model] = False  # 실패 시 재시도 가능


def _client(model_alias: ModelLiteral) -> OpenAI:
    """OpenAI 호환 클라이언트. mlx_vlm.server는 인증을 안 보지만 SDK가 키를 요구."""
    return OpenAI(base_url=_mlx_server.base_url(model_alias), api_key="not-needed")


def _to_data_url(image_path: Path) -> str:
    """이미지 파일 → ``data:<mime>;base64,...`` URL.

    OpenAI vision content array 표준 (``{"type": "image_url", "image_url":
    {"url": "data:..."}})`` 형식. mlx_vlm.server v0.4+가 이 표준 형식을
    그대로 받는다.
    """
    mime = mimetypes.guess_type(str(image_path))[0] or "image/png"
    data = image_path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _call_mlx(img_path: Path, model: str, prompt: str, timeout: int) -> dict[str, Any]:
    """mlx_vlm.server `/v1/chat/completions` 호출 + 표준화된 응답 dict 반환."""
    alias = cast(ModelLiteral, model)
    client = _client(alias)
    data_url = _to_data_url(img_path)
    mpath = _mlx_server.model_path(alias)

    resp = client.chat.completions.create(
        model=mpath,
        messages=cast(
            Any,
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
        ),
        max_tokens=_MAX_OUTPUT_TOKENS,
        timeout=timeout,
    )
    content = resp.choices[0].message.content or ""
    return {"message": {"content": content}}


def _default_prompt(schema: dict[str, Any] | None) -> str:
    """schema가 있으면 JSON 키 안내, 없으면 일반 OCR.

    mlx_vlm.server는 ``response_format: json_object`` 미지원이라 프롬프트로
    JSON-only 출력을 강제하고, ``_parse_response``에서 코드펜스를 제거한다.
    """
    if schema and "properties" in schema:
        keys = list(schema["properties"].keys())
        return (
            f"이 이미지의 텍스트를 OCR하여 다음 JSON 키로 구조화하세요: {keys}. "
            "결과는 valid JSON만 반환하세요 — 마크다운 코드펜스(```) 없이."
        )
    return "이 이미지의 모든 텍스트를 추출해주세요. (OCR)"


def _strip_code_fence(content: str) -> str:
    """``\\`\\`\\`json ... \\`\\`\\``` 같은 마크다운 코드펜스를 제거.

    mlx_vlm는 response_format JSON을 강제하지 못해 모델이 종종 ```json ... ```
    펜스로 감싼다. 단순한 fence(```/```json)만 제거 — 내부에 fence가 또 있는
    edge case는 jsonschema retry 채널에서 처리된다.
    """
    s = content.strip()
    if not s.startswith("```"):
        return s
    lines = s.splitlines()
    if len(lines) < 2:
        return s
    # 첫 줄(```json 또는 ```)을 버림. 마지막 줄이 ```이면 그것도 버림.
    body = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
    return "\n".join(body).strip()


def _parse_response(response: dict[str, Any], schema: dict[str, Any] | None) -> dict[str, Any]:
    """mlx 응답에서 content 추출 → 코드펜스 strip → JSON parse 시도.

    parse 실패 시 ``{"_raw_text": ..., "_parse_error": ...}`` 반환 + warning log.
    """
    content = ""
    msg = response.get("message")
    if isinstance(msg, dict):
        content = str(msg.get("content", ""))
    elif "response" in response:
        content = str(response["response"])

    cleaned = _strip_code_fence(content)
    log = demo_logger("ocr.gemma")
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
        return {"_raw_value": parsed}
    except (json.JSONDecodeError, TypeError) as e:
        log.warning(f"mlx response not valid JSON: {e}; raw={content!r}")
        return {"_raw_text": content, "_parse_error": str(e)}


def _safe_dummy(image_path: Path) -> dict[str, Any]:
    """deterministic dummy — image path hash 기반 (cache key 안정화)."""
    h = hashlib.sha1(str(image_path).encode()).hexdigest()[:8]
    return {
        "_safe": True,
        "qualname": "core.ocr.gemma.extract",
        "image_hash": h,
        "image_path": str(image_path),
    }
