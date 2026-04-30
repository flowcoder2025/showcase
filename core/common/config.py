"""환경변수 로딩 + 레포 루트 해석."""
import os
from pathlib import Path
from dotenv import dotenv_values


def repo_root() -> Path:
    """pyproject.toml이 있는 디렉토리를 레포 루트로 간주."""
    p = Path(__file__).resolve()
    for parent in [p, *p.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("repo root not found (no pyproject.toml in ancestors)")


def load() -> dict[str, str]:
    """`.env` + 실제 환경변수 병합. 실제 환경변수가 우선."""
    root = repo_root() if (Path.cwd() / "pyproject.toml").exists() else Path.cwd()
    env_file = root / ".env" if (root / ".env").exists() else Path.cwd() / ".env"
    file_vals = dotenv_values(env_file) if env_file.exists() else {}
    merged = {**file_vals, **{k: v for k, v in os.environ.items() if k in file_vals}}
    return {k: v for k, v in merged.items() if v is not None}
