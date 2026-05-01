"""거래처 × 월 피벗."""

import pandas as pd


def vendor_by_month(df: pd.DataFrame) -> pd.DataFrame:
    """vendor/date/amount 컬럼을 가진 DataFrame을 vendor × YYYY-MM 합계 표로."""
    work = df.copy()
    work["month"] = work["date"].dt.strftime("%Y-%m")
    pivot = work.pivot_table(
        index="vendor", columns="month", values="amount", aggfunc="sum", fill_value=0
    )
    return pivot
