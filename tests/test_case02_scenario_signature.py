"""T38 — case02 scenario signature smoke test."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from flowcoder_office_tools.protocols import ScenarioResult

from cases.case02_excel_invoice_validation import scenario


def test_case02_returns_scenario_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from flowcoder_office_tools.messaging import discord

    monkeypatch.setattr(discord, "send", lambda *a, **k: {"status": 204})

    in_dir = tmp_path / "in"
    in_dir.mkdir()
    df = pd.DataFrame(
        [
            {
                "거래처명": "A",
                "거래명세서번호": "INV-1",
                "품목": "X",
                "단가": 1000,
                "수량": 10,
                "금액": 10_000,
            },
        ]
    )
    df.to_excel(in_dir / "invoices.xlsx", index=False)

    result: ScenarioResult = scenario.run(
        input_dir=in_dir,
        output_dir=tmp_path / "out",
        config={"discord_alert": False},
    )
    assert result["case_id"] == "case02"
    assert all(p.exists() for p in result["output_files"])
    assert "flagged" in result["metrics"]
    _: dict[str, Any] = result["extras"]
