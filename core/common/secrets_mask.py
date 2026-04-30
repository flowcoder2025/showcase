"""시연 시 시크릿 마스킹 헬퍼.

목적: 시연 화면에 webhook URL/API 키 노출 방지.
규칙: 코드에서 시크릿을 `print()`/`log.info()`에 직접 넣는 패턴은 ruff 룰로 차단(추후 추가).

지원 포맷: Discord webhook, OpenRouter/Anthropic/OpenAI API 키, GitHub PAT,
Slack 토큰, AWS access/session 키, JWT, generic Bearer 헤더.
"""
import re

DISCORD_WEBHOOK_RE = re.compile(r"(https://discord\.com/api/webhooks/)[\w\-/.]+")
OPENROUTER_KEY_RE = re.compile(r"(sk-or-)[\w\-]{4,}")
ANTHROPIC_KEY_RE = re.compile(r"(sk-ant-)[\w\-]{4,}")
OPENAI_KEY_RE = re.compile(r"sk-(?:proj-|svcacct-)?[A-Za-z0-9_\-]{20,}")
GITHUB_TOKEN_RE = re.compile(r"\b(gh[pousr]|github_pat)_[A-Za-z0-9_]{20,}")
SLACK_TOKEN_RE = re.compile(r"\b(xox[baprs])-[A-Za-z0-9\-]{10,}")
AWS_ACCESS_KEY_RE = re.compile(r"\b(AKIA|ASIA)[A-Z0-9]{16}\b")
JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\b")
GENERIC_BEARER_RE = re.compile(r"(Bearer\s+)[A-Za-z0-9_\-]{8,}\b")


def mask(value: str) -> str:
    """단일 토큰을 인식해 마스킹된 값으로 반환. 비시크릿이면 원본 반환."""
    if not isinstance(value, str):
        return value
    s = value
    s = DISCORD_WEBHOOK_RE.sub(r"\1***", s)
    # Specific sk-* shapes BEFORE generic OpenAI sk- to preserve their prefixes.
    s = OPENROUTER_KEY_RE.sub(r"\1***", s)
    s = ANTHROPIC_KEY_RE.sub(r"\1***", s)
    s = OPENAI_KEY_RE.sub("sk-***", s)
    s = GITHUB_TOKEN_RE.sub(r"\1_***", s)
    s = SLACK_TOKEN_RE.sub(r"\1-***", s)
    s = AWS_ACCESS_KEY_RE.sub(r"\1***", s)
    s = JWT_RE.sub("eyJ***", s)
    s = GENERIC_BEARER_RE.sub(r"\1***", s)
    return s


def mask_text(text: str) -> str:
    """문장 안의 시크릿 inline 치환."""
    return mask(text)
