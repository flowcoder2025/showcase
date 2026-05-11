from pathlib import Path

import pytest
from flowcoder_office_tools.common import safe_mode


def test_intercept_isolates_between_two_cases(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """case A에서 patch한 게 case B에 새지 않아야."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEMO_SAFE", "1")

    from flowcoder_office_tools.messaging import discord as discord_mod

    original_send = discord_mod.send

    with safe_mode.intercept("caseA", apis=["discord_webhook"]):
        assert discord_mod.send is not original_send

    assert discord_mod.send is original_send  # 복원됨

    with safe_mode.intercept("caseB", apis=["discord_webhook"]):
        assert discord_mod.send is not original_send

    assert discord_mod.send is original_send
