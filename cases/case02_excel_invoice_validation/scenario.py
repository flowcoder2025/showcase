"""Case 02 — 거래명세서 단가 검증 + Discord 이상치 알림 (T38 signature)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd
from flowcoder_office_tools.backends.factory import default_backends, safe_backends
from flowcoder_office_tools.common import timer
from flowcoder_office_tools.common.demo_logger import demo_logger
from flowcoder_office_tools.common.safe_mode_v2 import is_safe
from flowcoder_office_tools.excel import validator
from flowcoder_office_tools.messaging import discord
from flowcoder_office_tools.progress import ProgressEvent
from flowcoder_office_tools.protocols import Backends, ScenarioResult

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
# Existing scenario reads single file `invoices.xlsx` under `invoices/`.
# Matrix line 92 says vendors/ — kept code path (functional preservation, T38).
_DEFAULT_IN = _REPO_ROOT / "personas/sample_data/invoices"
_DEFAULT_OUT = Path(__file__).resolve().parent / "output"
_OUTPUT_NAME = "outliers.xlsx"
_INPUT_NAME = "invoices.xlsx"


def run(
    *,
    input_dir: Path | None = None,
    output_dir: Path | None = None,
    backends: Backends | None = None,
    progress_cb: Callable[[ProgressEvent], None] | None = None,
    config: dict[str, Any] | None = None,
) -> ScenarioResult:
    in_dir = Path(input_dir) if input_dir else _DEFAULT_IN
    out_dir = Path(output_dir) if output_dir else _DEFAULT_OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    _ = backends or (safe_backends() if is_safe() else default_backends())  # T40 wire-up
    cfg = config or {}
    discord_alert = bool(cfg.get("discord_alert", True))
    input_path = in_dir / _INPUT_NAME
    output_path = out_dir / _OUTPUT_NAME

    log = demo_logger("case02")
    with timer.measure(log, "단가 이상치 검출", before_minutes=90):
        df = pd.read_excel(input_path)
        flagged = validator.detect_unit_price_outliers(
            df, group_col="품목", price_col="단가", threshold=2.0
        )
        flagged.to_excel(output_path, index=False)

    log.info(f"이상치 {len(flagged)}건 검출 → {output_path}")

    n_flagged = int(len(flagged))
    sent = False
    if discord_alert and n_flagged > 0:
        items = ", ".join(
            f"{r['거래처명']}({r['거래명세서번호']})" for _, r in flagged.head(5).iterrows()
        )
        discord.send(
            f"단가 이상치 {n_flagged}건 감지:\n{items}",
            level="warning",
            title="거래명세서 단가 이상치 알림",
        )
        log.success("Discord 알림 발송 완료")
        sent = True

    return {
        "case_id": "case02",
        "summary_text": f"단가 이상치 {n_flagged}건 → {output_path.name}",
        "output_files": [output_path],
        "metrics": {"flagged": n_flagged, "discord_sent": sent},
        "failures": [],
        "extras": {},
    }


if __name__ == "__main__":
    run()
