"""엑셀 파일 다중 로딩."""

from pathlib import Path

import pandas as pd


def read_dir(path: Path, *, glob: str = "*.xlsx") -> list[pd.DataFrame]:
    """디렉토리 내 모든 매칭 파일을 DataFrame 리스트로 반환."""
    return [pd.read_excel(f) for f in sorted(Path(path).glob(glob))]
