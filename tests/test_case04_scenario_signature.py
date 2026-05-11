"""T38 — case04 scenario signature smoke test."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from cases._protocols import ScenarioResult
from cases.case04_discord_overdue_alert import scenario


def test_case04_returns_scenario_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from core.messaging import discord

    monkeypatch.setattr(discord, "send_with_level", lambda **_: {"status": 204})

    in_dir = tmp_path / "in"
    in_dir.mkdir()
    df = pd.DataFrame(
        [
            {
                "거래처명": "A",
                "거래번호": "INV-1",
                "금액": 1_000_000,
                "납기일": "2026-04-01",
                "연체일": 7,
            }
        ]
    )
    df.to_excel(in_dir / "overdue_invoices.xlsx", index=False)

    result: ScenarioResult = scenario.run(input_dir=in_dir, output_dir=tmp_path / "out")
    assert result["case_id"] == "case04"
    assert result["output_files"] == []  # case04: Discord-only, no file output
    assert result["metrics"]["sent"] == 1
    assert "by_level" in result["extras"]
