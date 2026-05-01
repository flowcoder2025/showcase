"""거래명세서 단가 이상치 검출."""
import pandas as pd


def detect_unit_price_outliers(
    df: pd.DataFrame,
    *,
    group_col: str,
    price_col: str,
    threshold: float = 2.0,
) -> pd.DataFrame:
    """품목 그룹별로 단가 표준편차의 threshold배를 벗어난 행을 반환.

    그룹 크기가 2 이하면 검출 대상에서 제외.
    Leave-one-out z-score를 사용하여 outlier 자신이 std를 부풀리는
    문제를 방지한다.
    """
    flagged_idx = []
    for _, group in df.groupby(group_col):
        if len(group) < 3:
            continue
        for idx, row in group.iterrows():
            others = group.drop(idx)[price_col]
            mean = others.mean()
            std = others.std(ddof=0)
            if std == 0:
                continue
            if abs(row[price_col] - mean) > threshold * std:
                flagged_idx.append(idx)
    return df.loc[flagged_idx]
