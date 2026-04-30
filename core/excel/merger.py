"""거래처 단위 병합·집계."""
from pathlib import Path

import pandas as pd

from core.excel import reader

REQUIRED_KEYS = ("vendor", "date", "amount")


def merge_by_vendor(input_dir: Path, *, column_map: dict[str, str]) -> pd.DataFrame:
    """입력 디렉토리의 엑셀 파일들을 vendor 단위로 병합한 표 반환.

    column_map: {"vendor": "거래처명", "date": "거래일", "amount": "금액"} 식.
    출력 DataFrame은 정규화된 컬럼명(vendor/date/amount)으로 반환.
    """
    for k in REQUIRED_KEYS:
        if k not in column_map:
            raise ValueError(f"column_map missing required key: {k}")

    frames = reader.read_dir(Path(input_dir))
    if not frames:
        raise ValueError(f"no .xlsx files in {input_dir}")

    rows = []
    for df in frames:
        for k in REQUIRED_KEYS:
            src_col = column_map[k]
            if src_col not in df.columns:
                raise ValueError(f"missing column: {src_col} (mapped from {k})")
        rename = {column_map[k]: k for k in REQUIRED_KEYS}
        rows.append(df[list(column_map.values())].rename(columns=rename))

    merged = pd.concat(rows, ignore_index=True)
    merged["date"] = pd.to_datetime(merged["date"])
    return merged
