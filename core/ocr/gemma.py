"""Ollama Gemma 4 wrapper — 영수증/세금계산서 OCR.

NOTE: 외부 호출은 모듈 참조로 호출 (safe_mode patch 격리):
    from core.ocr import gemma
    gemma.extract(...)

INTERCEPT_TARGETS["ollama_gemma"] = ("core.ocr.gemma", "extract") — 단일 patch point.

Architecture
- ``warmup`` / ``_model_exists`` / ``_safe_dummy`` / ``_call_ollama`` / ``_parse_response``
  은 internal helper. 외부에서 직접 호출하지 않는다 (safe_mode가 ``extract``만 patch).
- client-side timeout: ``ollama.Options``는 generation params 전용이라 timeout을 받지
  못한다. 따라서 ``concurrent.futures.ThreadPoolExecutor`` + ``future.result(timeout=...)``
  로 wall-clock timeout을 강제한다 (R3-O2).
- 실패 시 모두 ``safe_mode.force_safe`` 호출 + ``_safe_dummy`` 반환 — 시연 흐름이
  깨지지 않게 한다.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import threading
from pathlib import Path
from typing import Any, Literal

import ollama

from core.common import safe_mode
from core.common.demo_logger import demo_logger

ModelLiteral = Literal["gemma4:e2b", "gemma4:e4b"]
_TIMEOUTS_SEC: dict[str, int] = {"gemma4:e2b": 15, "gemma4:e4b": 30}
_WARMUP_DONE: dict[str, bool] = {}
_WARMUP_LOCK = threading.Lock()


# -- public API -------------------------------------------------------------


def warmup(model: ModelLiteral = "gemma4:e2b") -> None:
    """백그라운드 thread로 더미 추론 1회 — 콜드스타트 회피.

    runner.py 시작 시점에 호출 (R1-O5 결정).
    이미 warmup 완료된 모델은 재실행 안 함 (idempotent, lock 보호).
    실패 시 ``_WARMUP_DONE[model]``을 False로 reset해 재시도 가능하게 한다.
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
        성공: ollama 응답을 schema 가이드로 파싱한 dict.
        실패: ``{"_safe": True, "qualname": ..., "image_hash": ...}`` (safe_dummy).

    Failure modes (모두 force_safe + dummy 반환):
        - ollama 모델 미설치 (``_model_exists`` False)
        - timeout (gemma4:e2b 15s, gemma4:e4b 30s — client-side concurrent.futures)
        - ``ollama.RequestError`` / ``ollama.ResponseError``
    """
    img_path = Path(image_path)
    if not _model_exists(model):
        safe_mode.force_safe(f"ollama model {model} missing")
        return _safe_dummy(img_path)

    timeout = _TIMEOUTS_SEC[model]
    user_prompt = prompt or _default_prompt(schema)

    # NOTE: ``ThreadPoolExecutor.__exit__``는 모든 worker 완료까지 block한다.
    # timeout 시 즉시 반환해야 하므로 ``with`` 블록을 쓰지 않고 ``shutdown(wait=False)``로
    # 백그라운드 thread를 fire-and-forget 한다 (daemon-like). worker가 ollama
    # 호출에 갇혀도 메인 흐름은 차단되지 않는다.
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = pool.submit(_call_ollama, img_path, model, user_prompt)
        try:
            response = future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            safe_mode.force_safe(f"gemma {model} timeout {timeout}s")
            return _safe_dummy(img_path)
        except (ollama.RequestError, ollama.ResponseError) as e:
            safe_mode.force_safe(f"gemma {model} failed: {type(e).__name__}: {e}")
            return _safe_dummy(img_path)
        return _parse_response(response, schema)
    finally:
        pool.shutdown(wait=False)


# -- internal helpers -------------------------------------------------------


def _warmup_blocking(model: str) -> None:
    """동기 warmup. 실패는 silent (extract 호출 시 정식 처리)."""
    try:
        ollama.chat(
            model=model,
            messages=[{"role": "user", "content": "warmup"}],
        )
    except (ollama.RequestError, ollama.ResponseError):
        # extract() 호출 시 정식 force_safe 경로로 진입
        with _WARMUP_LOCK:
            _WARMUP_DONE[model] = False  # 실패 시 재시도 가능


def _model_exists(model: str) -> bool:
    """``ollama list``로 모델 설치 여부 확인.

    응답 shape는 SDK 버전에 따라 dict 또는 객체일 수 있어 양쪽 모두 처리.
    """
    try:
        listing: Any = ollama.list()
    except (ConnectionError, OSError, ollama.RequestError, ollama.ResponseError):
        return False

    models_raw: Any = (
        listing.get("models", []) if isinstance(listing, dict) else getattr(listing, "models", [])
    )
    prefix = model.split(":")[0]  # "gemma4"
    for m in models_raw:
        name = (
            (m.get("model") or m.get("name") or "")
            if isinstance(m, dict)
            else (getattr(m, "model", None) or getattr(m, "name", None) or "")
        )
        if name and str(name).startswith(prefix):
            return True
    return False


def _call_ollama(img_path: Path, model: str, prompt: str) -> dict[str, Any]:
    """``ollama.chat`` 호출 — 이미지 첨부 + JSON output 요청."""
    response: Any = ollama.chat(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt,
                "images": [str(img_path)],
            }
        ],
        format="json",  # ollama 0.4+ structured output
    )
    if isinstance(response, dict):
        return response
    # ollama._types.ChatResponse 객체 케이스
    msg = getattr(response, "message", None)
    content = getattr(msg, "content", "") if msg is not None else ""
    return {"message": {"content": content}}


def _default_prompt(schema: dict[str, Any] | None) -> str:
    """schema가 있으면 JSON 키 안내, 없으면 일반 OCR."""
    if schema and "properties" in schema:
        keys = list(schema["properties"].keys())
        return (
            f"이 이미지의 텍스트를 OCR하여 다음 JSON 키로 구조화하세요: {keys}. "
            "결과는 반드시 valid JSON으로 반환하세요."
        )
    return "이 이미지의 모든 텍스트를 추출해주세요. (OCR)"


def _parse_response(response: dict[str, Any], schema: dict[str, Any] | None) -> dict[str, Any]:
    """ollama 응답에서 content 추출 → JSON parse 시도.

    parse 실패 시 ``{"_raw_text": ..., "_parse_error": ...}`` 반환 + warning log.
    """
    content = ""
    msg = response.get("message")
    if isinstance(msg, dict):
        content = str(msg.get("content", ""))
    elif "response" in response:
        content = str(response["response"])

    log = demo_logger("ocr.gemma")
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return parsed
        # JSON valid but not a dict (e.g. list / scalar) → wrap
        return {"_raw_value": parsed}
    except (json.JSONDecodeError, TypeError) as e:
        log.warning(f"ollama response not valid JSON: {e}; raw={content!r}")
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
