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

    알고리즘 선택 (Leave-One-Out z-score):
        표준 groupby z-score는 outlier 자신이 그룹의 std/mean 통계에 포함되어
        통계량을 부풀리는 문제가 있다. 단일 outlier가 매우 클 경우, 자신이
        만들어낸 std로 자신을 평가하기 때문에 임계값 안쪽으로 떨어져
        검출되지 않을 수 있다.

        Leave-One-Out (LOO) 방식은 평가 대상 행을 제외한 나머지 행으로 mean/std를
        계산함으로써 이 inflation 문제를 해소한다. 작은 그룹에서도 outlier 1건이
        통계량을 흔들지 않으므로 더 안정적이다.

    Canonical regression case:
        ``[1000, 1100, 950, 1050, 15000] @ threshold=2.0``
            - Naive group-stat 방식: outlier 15000이 std를 부풀려 abs(diff)≈11180,
              2σ≈11180.45가 되어 boundary miss로 검출되지 않음.
            - LOO 방식: 15000을 제외한 [1000, 1100, 950, 1050]으로 std를
              계산하므로 명확하게 검출됨.

        See ``tests/test_validator.py::test_detect_handles_inflated_std_boundary``.
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
