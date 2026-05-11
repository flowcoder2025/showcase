import json
from pathlib import Path

import pytest


def test_case09_safe_mode_returns_deterministic_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """동일 입력 2회 실행 시 결과 동일 (T38: config["incoming_message"] 기반)."""
    monkeypatch.setenv("DEMO_SAFE", "1")

    incoming = "제목: 단가 문의\n본문: 안녕하세요. 단가표 부탁드립니다."

    # client.chat을 deterministic fake로 교체.
    fake_drafts = '[{"option": 1, "subject": "테스트 답신", "body": "본문"}]'
    from core.ai import client as ai_client

    monkeypatch.setattr(ai_client, "chat", lambda messages, **k: fake_drafts)

    from cases.case09_ai_email_drafter import scenario

    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"
    r1 = scenario.run(output_dir=out1, config={"incoming_message": incoming})
    r2 = scenario.run(output_dir=out2, config={"incoming_message": incoming})

    text1 = r1["output_files"][0].read_text(encoding="utf-8")
    text2 = r2["output_files"][0].read_text(encoding="utf-8")

    assert text1 == text2
    parsed = json.loads(text1)
    assert isinstance(parsed, list)
    assert len(parsed) >= 1
    assert parsed[0]["subject"] == "테스트 답신"


def test_case09_external_apis_listed_in_meta() -> None:
    import yaml

    meta = yaml.safe_load(Path("cases/case09_ai_email_drafter/meta.yaml").read_text())
    assert "openrouter" in meta.get("external_apis", [])
