from pathlib import Path

import pandas as pd

from core.excel import merger


def test_merger_reuses_with_english_columns(tmp_path: Path) -> None:
    """다음 컨설팅 프로젝트 시나리오 — 컬럼명이 영어인 경우."""
    df = pd.DataFrame(
        [
            {"Customer": "X", "TxDate": "2026-01-01", "Total": 100},
            {"Customer": "X", "TxDate": "2026-02-01", "Total": 200},
        ]
    )
    p = tmp_path
    df.to_excel(p / "data.xlsx", index=False)

    column_map = {"vendor": "Customer", "date": "TxDate", "amount": "Total"}
    result = merger.merge_by_vendor(p, column_map=column_map)
    assert result["amount"].sum() == 300
