from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.excel.reader import read_dir

REQUIRED_KEYS = ("vendor", "date", "amount")


def merge_by_vendor(input_dir: Path, *, column_map: dict[str, str]) -> pd.DataFrame:
    for k in REQUIRED_KEYS:
        if k not in column_map:
            raise ValueError(f"column_map missing required key: {k}")

    frames = read_dir(input_dir)
    renamed: list[pd.DataFrame] = []
    for df in frames:
        for k in REQUIRED_KEYS:
            src_col = column_map[k]
            if src_col not in df.columns:
                raise ValueError(
                    f"missing column: {src_col} (mapped from {k})"
                )
        renamed.append(
            df.rename(columns={column_map[k]: k for k in REQUIRED_KEYS})[
                list(REQUIRED_KEYS)
            ]
        )

    merged = pd.concat(renamed, ignore_index=True)
    merged["date"] = pd.to_datetime(merged["date"])
    return merged
