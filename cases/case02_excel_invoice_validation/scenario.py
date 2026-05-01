"""Case 02 — 거래명세서 단가 검증 + Discord 이상치 알림."""

from pathlib import Path

import pandas as pd

from core.common import timer
from core.common.demo_logger import demo_logger
from core.excel import validator
from core.messaging import discord


def run(
    input_path: Path | str = "personas/sample_data/invoices/invoices.xlsx",
    output_path: Path | str = "cases/case02_excel_invoice_validation/output/outliers.xlsx",
    discord_alert: bool = True,
) -> int:
    log = demo_logger("case02")
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with timer.measure(log, "단가 이상치 검출", before_minutes=90):
        df = pd.read_excel(input_path)
        flagged = validator.detect_unit_price_outliers(
            df, group_col="품목", price_col="단가", threshold=2.0
        )
        flagged.to_excel(output_path, index=False)

    log.info(f"이상치 {len(flagged)}건 검출 → {output_path}")

    if discord_alert and len(flagged) > 0:
        items = ", ".join(
            f"{r['거래처명']}({r['거래명세서번호']})" for _, r in flagged.head(5).iterrows()
        )
        discord.send(
            f"단가 이상치 {len(flagged)}건 감지:\n{items}",
            level="warning",
            title="거래명세서 단가 이상치 알림",
        )
        log.success("Discord 알림 발송 완료")
    return 0


if __name__ == "__main__":
    run()
