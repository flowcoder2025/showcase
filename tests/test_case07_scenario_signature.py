"""T38 — case07 scenario signature smoke test."""

from __future__ import annotations

from pathlib import Path

import pytest
from flowcoder_office_tools.protocols import ScenarioResult
from PIL import Image

from cases.case07_ocr_receipt_to_excel import scenario


def test_case07_returns_scenario_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from flowcoder_office_tools.ocr import receipt
    from flowcoder_office_tools.ocr.receipt import ReceiptData

    monkeypatch.setattr(
        receipt,
        "extract",
        lambda _p: ReceiptData(
            merchant="스타벅스",
            amount=5500,
            date="2026-04-15",
            items=[],
            raw_text="스타벅스 5500",
        ),
    )

    in_dir = tmp_path / "in"
    in_dir.mkdir()
    img = in_dir / "r001.png"
    Image.new("RGB", (10, 10), "white").save(img)

    result: ScenarioResult = scenario.run(input_dir=in_dir, output_dir=tmp_path / "out")
    assert result["case_id"] == "case07"
    assert len(result["output_files"]) == 1
    assert result["output_files"][0].name == "expense_report.xlsx"
    assert result["metrics"]["processed"] == 1
    assert "receipts" in result["extras"]
