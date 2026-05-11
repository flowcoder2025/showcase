"""case04 — 미수금 단계별 Discord 알림 (T38 ScenarioResult signature).

연체일에 따라 4단계 톤을 분기해 Discord 채널에 알림을 발송한다. 출력 파일 0
(Discord 발송만) — output_files는 빈 리스트.

Architecture
- thin wrapper: pandas 직접 + core.messaging.discord
- 단일 patch point: ``discord.send`` (``send_with_level``이 내부적으로 호출).
- column_map 강제 (config["column_map"]).
- webhook_url override (config["webhook_url"]).
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd
import rich.markup

from cases._protocols import Backends, ScenarioResult
from core.backends.factory import default_backends, safe_backends
from core.common import timer
from core.common.demo_logger import demo_logger
from core.common.safe_mode_v2 import is_safe
from core.messaging import discord
from core.progress import ProgressEvent

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_IN = _REPO_ROOT / "personas/sample_data"
_DEFAULT_OUT = Path(__file__).resolve().parent / "output"
_INPUT_NAME = "overdue_invoices.xlsx"

COLUMN_MAP = {
    "vendor": "거래처명",
    "invoice_id": "거래번호",
    "amount": "금액",
    "due_date": "납기일",
    "days_overdue": "연체일",
}


def classify_level(days: int) -> discord.OverdueLevelLiteral:
    """연체일 → 4단계 톤 분기 (0~14 friendly / 15~30 neutral / 31~60 strict / 60+ final)."""
    if days < 0:
        raise ValueError(f"negative days_overdue: {days}")
    if days <= 14:
        return "friendly"
    if days <= 30:
        return "neutral"
    if days <= 60:
        return "strict"
    return "final"


def _resolve_input_path(input_dir: Path | None) -> Path:
    if input_dir is not None:
        return Path(input_dir) / _INPUT_NAME
    case_dir = Path(__file__).resolve().parent
    cand = case_dir / "input" / _INPUT_NAME
    if cand.exists():
        return cand
    return _DEFAULT_IN / _INPUT_NAME


def run(
    *,
    input_dir: Path | None = None,
    output_dir: Path | None = None,
    backends: Backends | None = None,
    progress_cb: Callable[[ProgressEvent], None] | None = None,
    config: dict[str, Any] | None = None,
) -> ScenarioResult:
    """미수금 데이터 → 단계별 Discord 알림. output_files 빈 리스트 (Discord-only)."""
    out_dir = Path(output_dir) if output_dir else _DEFAULT_OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    _ = backends or (safe_backends() if is_safe() else default_backends())  # T40 wire-up
    cfg = config or {}
    cmap = {**COLUMN_MAP, **(cfg.get("column_map") or {})}
    url = cfg.get("webhook_url") or os.environ.get("DISCORD_WEBHOOK_URL")
    input_path = _resolve_input_path(input_dir)

    log = demo_logger("case04_discord_overdue_alert")
    df = pd.read_excel(input_path)
    sent_total = 0
    errors = 0
    by_level: dict[str, int] = {}

    with timer.measure(log, "미수금 단계별 Discord 알림", before_minutes=120):
        for _, row in df.iterrows():
            try:
                level = classify_level(int(row[cmap["days_overdue"]]))
                vendor_safe = rich.markup.escape(str(row[cmap["vendor"]]))
                amount = int(row[cmap["amount"]])
                days = int(row[cmap["days_overdue"]])
                discord.send_with_level(
                    webhook_url=url,
                    title=f"[{level.upper()}] {vendor_safe} 미수금",
                    body=f"{amount:,}원 / 연체 {days}일",
                    level=level,
                )
                sent_total += 1
                by_level[level] = by_level.get(level, 0) + 1
            except Exception as e:  # noqa: BLE001 — per-row 실패가 전체를 막지 않게 함
                log.warning(f"row failed: {e}")
                errors += 1

    log.success(f"전송 {sent_total}건 / 실패 {errors}건")
    return {
        "case_id": "case04",
        "summary_text": f"Discord {sent_total}건 발송 / 실패 {errors}건",
        "output_files": [],
        "metrics": {"sent": sent_total, "errors": errors},
        "failures": [],
        "extras": {"by_level": by_level},
    }


if __name__ == "__main__":
    run()
