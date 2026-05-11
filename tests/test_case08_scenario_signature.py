"""T38 — case08 scenario signature smoke test."""

from __future__ import annotations

from pathlib import Path

import pytest
from flowcoder_office_tools.protocols import ScenarioResult
from PIL import Image

from cases.case08_ocr_invoice_to_csv import scenario


def test_case08_returns_scenario_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from flowcoder_office_tools.ocr import invoice
    from flowcoder_office_tools.ocr.invoice import InvoiceData

    monkeypatch.setattr(
        invoice,
        "extract",
        lambda _p: InvoiceData(
            invoice_no="INV-001",
            issue_date="2026-04-01",
            supplier_biznum="220-81-62517",
            supplier_name="공급자",
            buyer_biznum="120-81-47521",
            buyer_name="공급받는자",
            line_items=[],
            total_supply=1_000_000,
            total_vat=100_000,
            total_amount=1_100_000,
        ),
    )

    in_dir = tmp_path / "in"
    in_dir.mkdir()
    img = in_dir / "inv_001.png"
    Image.new("RGB", (10, 10), "white").save(img)

    result: ScenarioResult = scenario.run(input_dir=in_dir, output_dir=tmp_path / "out")
    assert result["case_id"] == "case08"
    assert len(result["output_files"]) == 3  # utf8 + cp949 + failures json
    assert result["metrics"]["processed"] == 1
    assert result["metrics"]["verified"] == 1
    assert "invoices" in result["extras"]
