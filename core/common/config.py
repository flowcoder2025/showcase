"""환경변수 로딩 + 레포 루트 해석."""
import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv


def repo_root() -> Path:
    """pyproject.toml이 있는 디렉토리를 레포 루트로 간주."""
    p = Path(__file__).resolve()
    for parent in [p, *p.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("repo root not found (no pyproject.toml in ancestors)")


def load() -> dict[str, str]:
    """Schema-driven 환경 로드.

    `.env` 파일에 선언된 키들만 반환한다 — `.env`가 schema 역할.
    같은 키가 os.environ에도 있으면 os.environ 값으로 override.
    `.env`에 없는 os.environ 변수는 결과에서 제외 (PATH, HOME 등 무관 변수 차단).

    부수 효과: `.env` 파일이 존재하면 os.environ에 주입한다 (load_dotenv).
    이로써 runner.py 등 호출자는 별도로 load_dotenv()를 호출할 필요가 없다.

    Returns:
        dict[str, str]: schema 키와 해소된 값의 매핑.
    """
    root = repo_root() if (Path.cwd() / "pyproject.toml").exists() else Path.cwd()
    env_file = root / ".env" if (root / ".env").exists() else Path.cwd() / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=False)
    file_vals = dotenv_values(env_file) if env_file.exists() else {}
    merged = {**file_vals, **{k: v for k, v in os.environ.items() if k in file_vals}}
    return {k: v for k, v in merged.items() if v is not None}
