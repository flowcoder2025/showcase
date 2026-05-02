"""case04 — 미수금 단계별 Discord 알림.

연체일에 따라 4단계 톤을 분기해 Discord 채널에 알림을 발송한다.

Architecture
- thin wrapper: core.excel.reader (없으므로 pandas 직접) + core.messaging.discord
- 단일 patch point: ``discord.send`` (``send_with_level``이 내부적으로 호출).
- column_map 강제: 다른 입력 스키마에서도 동일 시나리오 재호출 가능.

NOTE: 외부 호출은 모듈 참조로 호출(safe_mode patch 격리):
    from core.messaging import discord
    discord.send_with_level(...)
"""

import os
from pathlib import Path
from typing import Any

import pandas as pd
import rich.markup

from core.common import timer
from core.common.demo_logger import demo_logger
from core.messaging import discord

# column_map: 기본 스키마 (다른 입력에선 호출 측이 override 가능).
COLUMN_MAP = {
    "vendor": "거래처명",
    "invoice_id": "거래번호",
    "amount": "금액",
    "due_date": "납기일",
    "days_overdue": "연체일",
}


def classify_level(days: int) -> discord.OverdueLevelLiteral:
    """연체일 → 4단계 톤 분기.

    - 0~14일:  friendly  (info, blue)
    - 15~30일: neutral   (warning, orange)
    - 31~60일: strict    (danger, red)
    - 60+일:   final     (critical, black — 법무 escalation)

    음수 입력은 데이터 오염으로 간주하고 ValueError를 던진다.
    """
    if days < 0:
        raise ValueError(f"negative days_overdue: {days}")
    if days <= 14:
        return "friendly"
    if days <= 30:
        return "neutral"
    if days <= 60:
        return "strict"
    return "final"


def run(
    input_path: Path | str | None = None,
    *,
    webhook_url: str | None = None,
    column_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """미수금 데이터 → 단계별 Discord 알림.

    Returns
    -------
    summary : dict
        ``{"sent": int, "by_level": {level: int}, "errors": int}``
    """
    log = demo_logger("case04_discord_overdue_alert")
    case_dir = Path(__file__).parent
    # 부분 override 허용 (case03/case05 패턴 일치). dict | dict 병합으로
    # 누락 키는 default COLUMN_MAP에서 채워진다 — `column_map={"vendor": "..."}`
    # 같은 single-key override 시 silent KeyError 트랩 방지.
    cmap = {**COLUMN_MAP, **(column_map or {})}

    if input_path is None:
        # 우선 case 입력 → 없으면 sample_data fallback.
        candidate = case_dir / "input" / "overdue_invoices.xlsx"
        if candidate.exists():
            input_path = candidate
        else:
            input_path = Path("personas/sample_data/overdue_invoices.xlsx")

    df = pd.read_excel(Path(input_path))
    summary: dict[str, Any] = {"sent": 0, "by_level": {}, "errors": 0}
    url = webhook_url or os.environ.get("DISCORD_WEBHOOK_URL")

    with timer.measure(log, "미수금 단계별 Discord 알림", before_minutes=120):
        for _, row in df.iterrows():
            try:
                level = classify_level(int(row[cmap["days_overdue"]]))
                # rich.markup 안전: vendor 명에 [..] 포함 시 콘솔에서 markup 해석되는 걸 방지.
                vendor_safe = rich.markup.escape(str(row[cmap["vendor"]]))
                amount = int(row[cmap["amount"]])
                days = int(row[cmap["days_overdue"]])
                discord.send_with_level(
                    webhook_url=url,
                    title=f"[{level.upper()}] {vendor_safe} 미수금",
                    body=f"{amount:,}원 / 연체 {days}일",
                    level=level,
                )
                summary["sent"] = int(summary["sent"]) + 1
                by_level: dict[str, int] = summary["by_level"]
                by_level[level] = by_level.get(level, 0) + 1
            except Exception as e:  # noqa: BLE001 — per-row 실패가 전체를 막지 않게 함
                log.warning(f"row failed: {e}")
                summary["errors"] = int(summary["errors"]) + 1

    log.success(f"전송 {summary['sent']}건 / 실패 {summary['errors']}건")
    return summary


if __name__ == "__main__":
    run()
