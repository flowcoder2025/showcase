import pandas as pd

from core.excel import validator


def test_detect_unit_price_outliers_flags_3std() -> None:
    df = pd.DataFrame({
        "품목": ["A", "A", "A", "A", "A"],
        "단가": [1000, 1100, 950, 1050, 15000],  # 마지막이 명백한 outlier (5σ+)
    })
    flagged = validator.detect_unit_price_outliers(
        df, group_col="품목", price_col="단가", threshold=2.0,
    )
    assert len(flagged) == 1
    assert flagged.iloc[0]["단가"] == 15000


def test_detect_handles_single_item_groups() -> None:
    df = pd.DataFrame({"품목": ["B"], "단가": [500]})
    flagged = validator.detect_unit_price_outliers(df, group_col="품목", price_col="단가")
    assert len(flagged) == 0


def test_detect_handles_inflated_std_boundary() -> None:
    """Regression: spec test [1000,1100,950,1050,15000] @ thr=2.0
    fails with naive group-std (15000 inflates std). LOO z-score correctly flags 15000.
    """
    df = pd.DataFrame({
        "품목": ["A"] * 5,
        "단가": [1000, 1100, 950, 1050, 15000],
    })
    flagged = validator.detect_unit_price_outliers(
        df, group_col="품목", price_col="단가", threshold=2.0
    )
    assert list(flagged["단가"]) == [15000]
