import pandas as pd

from core.excel import validator


def test_detect_unit_price_outliers_flags_3std():
    df = pd.DataFrame({
        "품목": ["A", "A", "A", "A", "A"],
        "단가": [1000, 1100, 950, 1050, 15000],  # 마지막이 명백한 outlier (5σ+)
    })
    flagged = validator.detect_unit_price_outliers(
        df, group_col="품목", price_col="단가", threshold=2.0,
    )
    assert len(flagged) == 1
    assert flagged.iloc[0]["단가"] == 15000


def test_detect_handles_single_item_groups():
    df = pd.DataFrame({"품목": ["B"], "단가": [500]})
    flagged = validator.detect_unit_price_outliers(df, group_col="품목", price_col="단가")
    assert len(flagged) == 0
