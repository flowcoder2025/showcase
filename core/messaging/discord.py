"""Discord webhook 발송 — 단계별 톤(level) 분기 지원.

NOTE: 외부 호출은 반드시 모듈 참조로 호출 (safe_mode patch 격리):
    from core.messaging import discord
    discord.send(...)
"""

import os
from typing import TypedDict

from discord_webhook import DiscordEmbed, DiscordWebhook

LEVEL_COLORS = {
    "info": "3498db",  # blue
    "success": "2ecc71",  # green
    "warning": "f39c12",  # orange
    "danger": "e74c3c",  # red
}


class SendResult(TypedDict):
    status: int | None


def send(
    content: str, *, level: str = "info", title: str | None = None, webhook_url: str | None = None
) -> SendResult:
    """Discord 채널에 메시지 전송. level이 주어지면 컬러 임베드 사용.

    반환: {"status": int}
    """
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
    return {"status": getattr(resp, "status_code", None)}
