from __future__ import annotations

from pathlib import Path

import pandas as pd


def read_dir(path: Path, *, glob: str = "*.xlsx") -> list[pd.DataFrame]:
    return [pd.read_excel(p) for p in sorted(Path(path).glob(glob))]
