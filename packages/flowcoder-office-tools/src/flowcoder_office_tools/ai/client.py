"""OpenRouter (primary) + OpenAI (fallback) 단일 진입점 + 모델 폴백.

모든 외부 호출은 모듈 참조로 호출해야 한다 (safe_mode patch 격리):
    from flowcoder_office_tools.ai import client
    client.chat(...)

Provider resolution:
    1. ``OPENROUTER_API_KEY`` 존재 → OpenRouter (``MODEL_PRIORITY`` 3-chain)
    2. ``OPENAI_API_KEY`` 존재 → OpenAI 직접 (``OPENAI_MODEL_PRIORITY``)
    3. 둘 다 부재 → ``force_safe`` → ``"[SAFE-FALLBACK]"``

``MODEL_PRIORITY`` 이름은 backward compat 유지 (Phase 2 DoD test + 외부
caller 다수). OpenRouter chain 의 의미 보존. OpenAI 직접 호출 시 chain 은
``OPENAI_MODEL_PRIORITY`` 가 사용된다.
"""

import os
from typing import Any, cast

from openai import APIStatusError, OpenAI
from openai import RateLimitError as OpenAIRateLimitError

from flowcoder_office_tools.common import safe_mode

MODEL_PRIORITY: tuple[str, ...] = (
    "google/gemini-2.5-flash",  # primary
    "anthropic/claude-haiku-4-5",  # fallback 1
    "openai/gpt-4o-mini",  # fallback 2
)

OPENAI_MODEL_PRIORITY: tuple[str, ...] = (
    "gpt-4o-mini",  # cost-effective default
    "gpt-4.1-mini",  # secondary fallback
)


class RateLimitError(Exception):
    pass


class ServerError(Exception):
    pass


def _resolve_provider() -> tuple[str, str | None, str, tuple[str, ...]]:
    """Return (provider, base_url, api_key, priority).

    OpenRouter 키 우선, 없으면 OpenAI 키, 둘 다 없으면 ``("none", ...)``.
    ``provider == "none"`` 일 때 caller(:func:`chat`) 가 ``force_safe`` 분기로
    빠진다.
    """
    or_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if or_key:
        return ("openrouter", "https://openrouter.ai/api/v1", or_key, MODEL_PRIORITY)
    oa_key = os.getenv("OPENAI_API_KEY", "").strip()
    if oa_key:
        return ("openai", None, oa_key, OPENAI_MODEL_PRIORITY)
    return ("none", None, "", ())


def _make_client() -> OpenAI:
    _, base_url, api_key, _ = _resolve_provider()
    if base_url is None:
        # OpenAI default base_url + api.openai.com — OpenAI SDK 기본 동작.
        return OpenAI(api_key=api_key)
    return OpenAI(base_url=base_url, api_key=api_key)


def _call(model: str, messages: list[dict[str, Any]], **kwargs: Any) -> str:
    """단일 모델 호출. 429/5xx 시 RateLimitError/ServerError 발생.

    Typed openai 예외로 분류 — 문자열 매칭에 의존하지 않는다:
    - openai.RateLimitError → RateLimitError
    - openai.APIStatusError(status_code in 5xx) → ServerError
    - 그 외 모든 예외는 propagate (fail-loud).
    """
    try:
        resp = _make_client().chat.completions.create(
            model=model, messages=cast(Any, messages), **kwargs
        )
        return resp.choices[0].message.content or ""
    except OpenAIRateLimitError as e:
        raise RateLimitError(str(e)) from e
    except APIStatusError as e:
        if e.status_code in {500, 502, 503, 504}:
            raise ServerError(str(e)) from e
        raise


def chat(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    case_id: str | None = None,
    **kwargs: Any,
) -> str:
    """Provider 우선순위 + 모델 폴백 + 전부 실패 시 force_safe 후 더미 응답.

    case_id가 주어지고 DEMO_SAFE=0(라이브)이면 결과를 시연 캐시에 저장.

    Safe-mode short-circuit: DEMO_SAFE=1이면 네트워크 호출 없이 즉시
    "[SAFE-FALLBACK]"을 반환한다. 이는 runner.py::intercept 래핑 없이
    scenario.run()을 직접 실행하는 경우(테스트/CLI)에도 안전성을 보장한다.

    Note: 401/AuthenticationError, 모델 미존재 등 분류되지 않은 에러는
    그대로 propagate한다 (fail-loud). 폴백+더미 응답은 429/5xx에만 적용.
    Provider 가 ``"none"`` (두 키 모두 부재) 이면 즉시 ``force_safe`` 분기.
    """
    if safe_mode.is_safe():
        return "[SAFE-FALLBACK]"

    provider, _, _, default_priority = _resolve_provider()
    if provider == "none" and model is None:
        safe_mode.force_safe("no API key configured — set OPENROUTER_API_KEY or OPENAI_API_KEY")
        return "[SAFE-FALLBACK]"

    candidates = [model] if model else list(default_priority)
    last_err: Exception | None = None
    for m in candidates:
        try:
            result = _call(m, messages, **kwargs)
            if case_id and not safe_mode.is_safe():
                # messages는 list[dict]라 stable hash 위해 str화
                safe_mode.save_cache(
                    case_id,
                    "flowcoder_office_tools.ai.client.chat",
                    (),
                    {"messages_repr": repr(messages)},
                    result,
                )
            return result
        except (RateLimitError, ServerError) as e:
            last_err = e
            continue
    safe_mode.force_safe(f"all {provider} models failed: {last_err}")
    return "[SAFE-FALLBACK]"
