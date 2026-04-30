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
