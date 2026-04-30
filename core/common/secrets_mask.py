"""시연 시 시크릿 마스킹 헬퍼.

목적: 시연 화면에 webhook URL/API 키 노출 방지.
규칙: 코드에서 시크릿을 `print()`/`log.info()`에 직접 넣는 패턴은 ruff 룰로 차단(추후 추가).
"""
import re

DISCORD_WEBHOOK_RE = re.compile(r"(https://discord\.com/api/webhooks/)[\w\-/.]+")
OPENROUTER_KEY_RE = re.compile(r"(sk-or-)[\w\-]{4,}")
ANTHROPIC_KEY_RE = re.compile(r"(sk-ant-)[\w\-]{4,}")
GENERIC_BEARER_RE = re.compile(r"(Bearer\s+)[\w\-\.]{8,}")


def mask(value: str) -> str:
    """단일 토큰을 인식해 마스킹된 값으로 반환. 비시크릿이면 원본 반환."""
    if not isinstance(value, str):
        return value
    s = value
    s = DISCORD_WEBHOOK_RE.sub(r"\1***", s)
    s = OPENROUTER_KEY_RE.sub(r"\1***", s)
    s = ANTHROPIC_KEY_RE.sub(r"\1***", s)
    s = GENERIC_BEARER_RE.sub(r"\1***", s)
    return s


def mask_text(text: str) -> str:
    """문장 안의 시크릿 inline 치환."""
    return mask(text)
