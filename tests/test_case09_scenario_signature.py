"""T38 — case09 scenario signature smoke test (incoming_message via config)."""

from __future__ import annotations

from pathlib import Path

import pytest
from flowcoder_office_tools.protocols import ScenarioResult

from cases.case09_ai_email_drafter import scenario


def test_case09_returns_scenario_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from flowcoder_office_tools.ai import client as ai_client

    fake_drafts = '[{"option": 1, "subject": "테스트", "body": "본문"}]'
    monkeypatch.setattr(ai_client, "chat", lambda messages, **k: fake_drafts)

    result: ScenarioResult = scenario.run(
        output_dir=tmp_path / "out",
        config={"incoming_message": "제목: t\n본문: b"},
    )
    assert result["case_id"] == "case09"
    assert len(result["output_files"]) == 1
    assert result["output_files"][0].name == "drafts.json"
    assert result["metrics"]["drafts"] == 1
