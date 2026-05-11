"""Discord webhook 발송 — 단계별 톤(level) 분기 지원.

NOTE: 외부 호출은 반드시 모듈 참조로 호출 (safe_mode patch 격리):
    from flowcoder_office_tools.messaging import discord
    discord.send(...)
"""

import os
from typing import Literal, TypedDict

from discord_webhook import DiscordEmbed, DiscordWebhook

from flowcoder_office_tools.common.demo_logger import demo_logger

LEVEL_COLORS = {
    "info": "3498db",  # blue
    "success": "2ecc71",  # green
    "warning": "f39c12",  # orange
    "danger": "e74c3c",  # red
    "critical": "000000",  # black — case04 final escalation 단계
}

# case04 (미수금 단계별 알림) 도메인 level → internal level 매핑.
# 단일 patch point 보존: send_with_level()은 내부에서 send()를 호출한다.
OverdueLevelLiteral = Literal["friendly", "neutral", "strict", "final"]
OVERDUE_LEVEL_TO_INTERNAL: dict[str, str] = {
    "friendly": "info",  # 0~14일
    "neutral": "warning",  # 15~30일
    "strict": "danger",  # 31~60일
    "final": "critical",  # 60+일 (법무 escalation)
}


class SendResult(TypedDict):
    status: int | None


def send(
    content: str, *, level: str = "info", title: str | None = None, webhook_url: str | None = None
) -> SendResult:
    """Discord 채널에 메시지 전송. level이 주어지면 컬러 임베드 사용.

    반환: {"status": int}
    """
    # R2-M1: content와 title 둘 다 비어 있으면 Discord가 거절하기 전에 fail-fast.
    if (not content or not content.strip()) and not title:
        raise ValueError("send requires non-empty content or title")

    url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
    if not url:
        raise RuntimeError("DISCORD_WEBHOOK_URL not set")

    if title or level != "info":
        wh = DiscordWebhook(url=url)
        embed = DiscordEmbed(
            title=title or "알림",
            description=content,
            color=LEVEL_COLORS.get(level, LEVEL_COLORS["info"]),
        )
        wh.add_embed(embed)
    else:
        wh = DiscordWebhook(url=url, content=content)

    resp = wh.execute()
    status: int | None = getattr(resp, "status_code", None)
    # 429(rate limit) 또는 5xx(서버 오류) 응답은 시연 가시성을 위해 warning을 남긴다.
    # raise하지 않는 이유: 시연 도중 알림 실패가 흐름을 끊지 않게 하기 위함.
    # demo_logger는 secrets_mask를 거치므로 webhook URL이 포함된 메시지도 안전하다.
    if status is not None and (status == 429 or 500 <= status < 600):
        demo_logger("discord").warning(
            f"discord webhook returned {status} (rate limit/server error)"
        )
    return {"status": status}


def send_with_level(
    *,
    webhook_url: str | None = None,
    title: str,
    body: str,
    level: OverdueLevelLiteral,
) -> SendResult:
    """case04 도메인용 단계별 톤 분기 wrapper.

    내부적으로 send()를 호출 — INTERCEPT_TARGETS["discord_webhook"]은 send만
    등록되어 있으므로 단일 patch point를 보존한다.
    """
    if level not in OVERDUE_LEVEL_TO_INTERNAL:
        raise KeyError(f"unknown overdue level: {level!r}")
    if not body or not body.strip():
        raise ValueError("body must not be empty")
    internal = OVERDUE_LEVEL_TO_INTERNAL[level]
    return send(
        content=body,
        level=internal,
        title=title,
        webhook_url=webhook_url,
    )
