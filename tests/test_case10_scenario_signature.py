"""T38 — case10 scenario signature smoke test."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cases._protocols import ScenarioResult
from cases.case10_ai_meeting_summarizer import scenario


def test_case10_returns_scenario_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from core.ai import tasks
    from core.ai.tasks import ActionItem, MeetingSummary

    monkeypatch.setattr(
        tasks,
        "summarize_meeting",
        lambda transcript, *, attendees, **k: MeetingSummary(
            summary="요약",
            action_items=[ActionItem(owner="김사장", task="x", due="")],
            decisions=[],
        ),
    )

    in_dir = tmp_path / "in"
    in_dir.mkdir()
    (in_dir / "m000.txt").write_text("회의록", encoding="utf-8")
    meta = [{"filename": "m000.txt", "attendees": ["김사장"]}]
    (in_dir / scenario.DEFAULT_META_FILENAME).write_text(
        json.dumps(meta, ensure_ascii=False), encoding="utf-8"
    )

    result: ScenarioResult = scenario.run(input_dir=in_dir, output_dir=tmp_path / "out")
    assert result["case_id"] == "case10"
    assert result["metrics"]["processed"] == 1
    assert len(result["output_files"]) == 1
    assert "files" in result["extras"]
    assert "summaries" in result["extras"]
