"""T38 — case05 scenario signature smoke test."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from flowcoder_office_tools.protocols import ScenarioResult

from cases.case05_doc_quote_generator import scenario


def test_case05_returns_scenario_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from flowcoder_office_tools.docgen import pdf as pdf_mod

    monkeypatch.setattr(
        pdf_mod, "md_to_pdf", lambda md, out, **_: Path(out).write_bytes(b"%PDF-1.4 stub")
    )

    in_dir = tmp_path / "in"
    in_dir.mkdir()
    df = pd.DataFrame(
        [
            {
                "견적번호": "Q-001",
                "거래처명": "A",
                "담당자": "x",
                "이메일": "x@example.com",
                "품목": "p1",
                "수량": 1,
                "단가": 1000,
                "납기일": "2026-06-30",
            }
        ]
    )
    df.to_excel(in_dir / "quote_requests.xlsx", index=False)

    result: ScenarioResult = scenario.run(input_dir=in_dir, output_dir=tmp_path / "out")
    assert result["case_id"] == "case05"
    assert result["metrics"]["docx_count"] == 1
    assert result["metrics"]["pdf_count"] == 1
    assert all(p.exists() for p in result["output_files"])
