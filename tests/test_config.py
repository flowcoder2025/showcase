import os
from pathlib import Path
from core.common import config


def test_load_env_returns_dict_with_known_keys(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("OPENROUTER_API_KEY=test123\nDISCORD_WEBHOOK_URL=https://example.com/webhook\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)

    cfg = config.load()

    assert cfg["OPENROUTER_API_KEY"] == "test123"
    assert cfg["DISCORD_WEBHOOK_URL"] == "https://example.com/webhook"


def test_root_path_resolves_to_repo_root():
    root = config.repo_root()
    assert (root / "pyproject.toml").exists()


def test_env_var_overrides_file_value(tmp_path, monkeypatch):
    """os.environ가 .env 값을 override하는지 확인."""
    env_file = tmp_path / ".env"
    env_file.write_text("OPENROUTER_API_KEY=from_file\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENROUTER_API_KEY", "from_env")

    cfg = config.load()
    assert cfg["OPENROUTER_API_KEY"] == "from_env"


def test_env_var_not_in_schema_is_excluded(tmp_path, monkeypatch):
    """`.env`에 없는 os.environ 변수는 결과에 포함되지 않음."""
    env_file = tmp_path / ".env"
    env_file.write_text("OPENROUTER_API_KEY=test\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("UNRELATED_VAR", "should_be_excluded")
    monkeypatch.setenv("PATH", "/random/path")  # PATH는 항상 set

    cfg = config.load()
    assert "UNRELATED_VAR" not in cfg
    assert "PATH" not in cfg
    assert cfg["OPENROUTER_API_KEY"] == "test"


def test_load_returns_empty_dict_when_no_env_file(tmp_path, monkeypatch):
    """`.env` 파일이 없으면 빈 dict 반환."""
    monkeypatch.chdir(tmp_path)  # tmp_path에는 .env 없음
    cfg = config.load()
    assert cfg == {}
