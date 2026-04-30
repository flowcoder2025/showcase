import pandas as pd

from core.excel import pivot


def test_vendor_month_pivot():
    df = pd.DataFrame({
        "vendor": ["A", "A", "B"],
        "date": pd.to_datetime(["2026-01-15", "2026-02-10", "2026-01-20"]),
        "amount": [100, 200, 300],
    })
    result = pivot.vendor_by_month(df)
    assert result.loc["A", "2026-01"] == 100
    assert result.loc["A", "2026-02"] == 200
    assert result.loc["B", "2026-01"] == 300
