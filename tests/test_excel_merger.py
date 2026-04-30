
import pandas as pd
import pytest

from core.excel import merger


@pytest.fixture
def vendor_files(tmp_path):
    df1 = pd.DataFrame([
        {"거래처명": "A상회", "거래일": "2026-01-15", "금액": 100_000},
        {"거래처명": "B상사", "거래일": "2026-01-20", "금액": 200_000},
    ])
    df2 = pd.DataFrame([
        {"거래처명": "A상회", "거래일": "2026-02-10", "금액": 150_000},
    ])
    df1.to_excel(tmp_path / "jan.xlsx", index=False)
    df2.to_excel(tmp_path / "feb.xlsx", index=False)
    return tmp_path


def test_merge_by_vendor_aggregates_amount(vendor_files):
    column_map = {"vendor": "거래처명", "date": "거래일", "amount": "금액"}
    result = merger.merge_by_vendor(vendor_files, column_map=column_map)
    a_total = result.loc[result["vendor"] == "A상회", "amount"].sum()
    assert a_total == 250_000


def test_merge_works_with_different_column_names(tmp_path):
    """재사용성 검증 — 다른 스키마로 호출해도 동작."""
    df = pd.DataFrame([
        {"Customer": "X", "TxDate": "2026-01-01", "Total": 50},
        {"Customer": "Y", "TxDate": "2026-01-02", "Total": 70},
    ])
    df.to_excel(tmp_path / "data.xlsx", index=False)

    column_map = {"vendor": "Customer", "date": "TxDate", "amount": "Total"}
    result = merger.merge_by_vendor(tmp_path, column_map=column_map)
    assert result["amount"].sum() == 120


def test_missing_required_column_raises(tmp_path):
    df = pd.DataFrame([{"이름": "A", "금액": 100}])  # 거래일 없음
    df.to_excel(tmp_path / "bad.xlsx", index=False)
    column_map = {"vendor": "이름", "date": "거래일", "amount": "금액"}
    with pytest.raises(ValueError, match="missing column"):
        merger.merge_by_vendor(tmp_path, column_map=column_map)
