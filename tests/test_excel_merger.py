from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from core.excel.merger import merge_by_vendor


@pytest.fixture
def vendor_files(tmp_path: Path) -> Path:
    jan = pd.DataFrame(
        {
            "거래처명": ["A상회", "B상회"],
            "일자": ["2024-01-05", "2024-01-12"],
            "공급가액": [100_000, 50_000],
        }
    )
    feb = pd.DataFrame(
        {
            "거래처명": ["A상회", "C상회"],
            "일자": ["2024-02-03", "2024-02-19"],
            "공급가액": [150_000, 75_000],
        }
    )
    jan.to_excel(tmp_path / "jan.xlsx", index=False)
    feb.to_excel(tmp_path / "feb.xlsx", index=False)
    return tmp_path


def test_merge_by_vendor_aggregates_amount(vendor_files: Path) -> None:
    column_map = {"vendor": "거래처명", "date": "일자", "amount": "공급가액"}
    result = merge_by_vendor(vendor_files, column_map=column_map)
    assert set(result.columns) >= {"vendor", "date", "amount"}
    assert result.loc[result["vendor"] == "A상회", "amount"].sum() == 250_000


def test_merge_works_with_different_column_names(tmp_path: Path) -> None:
    df = pd.DataFrame({"v": ["X"], "d": ["2024-03-01"], "a": [1000]})
    df.to_excel(tmp_path / "x.xlsx", index=False)
    result = merge_by_vendor(tmp_path, column_map={"vendor": "v", "date": "d", "amount": "a"})
    assert result.iloc[0]["vendor"] == "X"


def test_missing_required_column_raises(tmp_path: Path) -> None:
    pd.DataFrame({"v": ["X"], "a": [1]}).to_excel(tmp_path / "bad.xlsx", index=False)
    with pytest.raises(ValueError, match="missing column"):
        merge_by_vendor(tmp_path, column_map={"vendor": "v", "date": "d", "amount": "a"})
