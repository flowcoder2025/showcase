"""거래처 단위 병합·집계."""

from pathlib import Path

import pandas as pd

from flowcoder_office_tools.excel import reader

REQUIRED_KEYS = ("vendor", "date", "amount")


def merge_by_vendor(input_dir: Path, *, column_map: dict[str, str]) -> pd.DataFrame:
    """입력 디렉토리의 엑셀 파일들을 vendor 단위로 병합한 표 반환.

    column_map: {"vendor": "거래처명", "date": "거래일", "amount": "금액"} 식.
    출력 DataFrame은 정규화된 컬럼명(vendor/date/amount)으로 반환.
    """
    for k in REQUIRED_KEYS:
        if k not in column_map:
            raise ValueError(f"column_map missing required key: {k}")

    if not Path(input_dir).is_dir():
        raise FileNotFoundError(f"input_dir not found or not a directory: {input_dir}")

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
        # REQUIRED_KEYS만 select — column_map에 추가 키가 있어도 무시
        rows.append(df[[column_map[k] for k in REQUIRED_KEYS]].rename(columns=rename))

    merged = pd.concat(rows, ignore_index=True)
    # errors="raise" — pandas 버전별 기본값 차이를 명시화
    merged["date"] = pd.to_datetime(merged["date"], errors="raise")
    return merged
