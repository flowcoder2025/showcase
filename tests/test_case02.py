from pathlib import Path
from typing import Any

import pandas as pd
import pytest


@pytest.fixture
def invoices_input(tmp_path: Path) -> Path:
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
            {
                "거래처명": "B",
                "거래명세서번호": "INV-2",
                "품목": "X",
                "단가": 1100,
                "수량": 5,
                "금액": 5_500,
            },
            {
                "거래처명": "C",
                "거래명세서번호": "INV-3",
                "품목": "X",
                "단가": 950,
                "수량": 8,
                "금액": 7_600,
            },
            {
                "거래처명": "D",
                "거래명세서번호": "INV-4",
                "품목": "X",
                "단가": 1050,
                "수량": 2,
                "금액": 2_100,
            },
            # 마지막 행이 outlier (5σ+)
            {
                "거래처명": "E",
                "거래명세서번호": "INV-5",
                "품목": "X",
                "단가": 15000,
                "수량": 1,
                "금액": 15_000,
            },
        ]
    )
    p = tmp_path / "invoices.xlsx"
    df.to_excel(p, index=False)
    return p


def test_case02_run_detects_outliers_and_calls_discord(
    invoices_input: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cases.case02_excel_invoice_validation import scenario
    from core.messaging import discord

    sent: list[tuple[str, dict[str, Any]]] = []

    def _capture(content: str, **k: Any) -> dict[str, int]:
        sent.append((content, k))
        return {"status": 204}

    monkeypatch.setattr(discord, "send", _capture)

    out = tmp_path / "output" / "outliers.xlsx"
    scenario.run(input_path=invoices_input, output_path=out, discord_alert=True)

    assert out.exists()
    assert len(sent) >= 1
    assert any("이상치" in s[0] or "outlier" in s[0].lower() for s in sent)
