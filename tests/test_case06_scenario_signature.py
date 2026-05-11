"""T38 — case06 scenario signature smoke test."""

from __future__ import annotations

from pathlib import Path

import pytest
from flowcoder_office_tools.protocols import ScenarioResult

from cases.case06_hwpx_govt_form_filler import scenario

_TEMPLATE = (
    Path(__file__).parent.parent
    / "personas"
    / "sample_data"
    / "forms"
    / "grant_application_template.hwpx"
)


def test_case06_returns_scenario_result(tmp_path: Path) -> None:
    if not _TEMPLATE.exists():
        pytest.skip("HWPX template fixture missing")

    result: ScenarioResult = scenario.run(
        output_dir=tmp_path,
        config={"template_path": _TEMPLATE},
    )
    assert result["case_id"] == "case06"
    assert len(result["output_files"]) == 1
    assert result["output_files"][0].exists()
    assert result["output_files"][0].suffix == ".hwpx"
    assert "fields_filled" in result["metrics"]
