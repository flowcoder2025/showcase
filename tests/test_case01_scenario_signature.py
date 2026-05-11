"""T38 — case01 scenario signature smoke test (ScenarioResult contract)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from cases._protocols import ScenarioResult
from cases.case01_excel_vendor_report import scenario


def test_case01_returns_scenario_result(tmp_path: Path) -> None:
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    df = pd.DataFrame(
        [
            {"거래처명": "A", "거래일": "2026-01-15", "금액": 100},
            {"거래처명": "A", "거래일": "2026-02-10", "금액": 200},
            {"거래처명": "B", "거래일": "2026-01-20", "금액": 300},
        ]
    )
    df.to_excel(in_dir / "data.xlsx", index=False)

    result: ScenarioResult = scenario.run(input_dir=in_dir, output_dir=tmp_path / "out")
    assert result["case_id"] == "case01"
    assert all(p.exists() for p in result["output_files"])
    assert "rows" in result["metrics"]
    assert isinstance(result["summary_text"], str)
