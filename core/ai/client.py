"""OpenRouter 단일 진입점 + 모델 우선순위 폴백.

모든 외부 호출은 모듈 참조로 호출해야 한다 (safe_mode patch 격리):
    from core.ai import client
    client.chat(...)
"""
import os
from typing import Any, cast

from openai import APIStatusError, OpenAI
from openai import RateLimitError as OpenAIRateLimitError

from core.common import safe_mode

MODEL_PRIORITY: tuple[str, ...] = (
    "google/gemini-2.5-flash",      # primary
    "anthropic/claude-haiku-4-5",   # fallback 1
    "openai/gpt-4o-mini",           # fallback 2
)


class RateLimitError(Exception):
    pass


class ServerError(Exception):
    pass


def _make_client() -> OpenAI:
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY", ""),
    )


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
    """우선순위 모델 폴백 + 전부 실패 시 force_safe 후 더미 응답.

    case_id가 주어지고 DEMO_SAFE=0(라이브)이면 결과를 시연 캐시에 저장.

    Safe-mode short-circuit: DEMO_SAFE=1이면 네트워크 호출 없이 즉시
    "[SAFE-FALLBACK]"을 반환한다. 이는 runner.py::intercept 래핑 없이
    scenario.run()을 직접 실행하는 경우(테스트/CLI)에도 안전성을 보장한다.

    Note: 401/AuthenticationError, 모델 미존재 등 분류되지 않은 에러는
    그대로 propagate한다 (fail-loud). 폴백+더미 응답은 429/5xx에만 적용.
    """
    if safe_mode.is_safe():
        return "[SAFE-FALLBACK]"

    candidates = [model] if model else list(MODEL_PRIORITY)
    last_err: Exception | None = None
    for m in candidates:
        try:
            result = _call(m, messages, **kwargs)
            if case_id and not safe_mode.is_safe():
                # messages는 list[dict]라 stable hash 위해 str화
                safe_mode.save_cache(
                    case_id, "core.ai.client.chat", (),
                    {"messages_repr": repr(messages)}, result,
                )
            return result
        except (RateLimitError, ServerError) as e:
            last_err = e
            continue
    safe_mode.force_safe(f"all openrouter models failed: {last_err}")
    return "[SAFE-FALLBACK]"
