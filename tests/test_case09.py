import json
from pathlib import Path

import pytest


def test_case09_safe_mode_returns_deterministic_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """동일 입력 2회 실행 시 결과 동일 (강화: fake AI 응답으로 contract 검증)."""
    monkeypatch.setenv("DEMO_SAFE", "1")
    monkeypatch.chdir(tmp_path)

    # 입력 파일 생성
    case_dir = Path("cases/case09_ai_email_drafter")
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "input").mkdir(exist_ok=True)
    (case_dir / "output").mkdir(exist_ok=True)
    (case_dir / "input" / "sample_incoming.txt").write_text(
        "제목: 단가 문의\n본문: 안녕하세요. 단가표 부탁드립니다.",
        encoding="utf-8",
    )

    # client.chat을 deterministic fake로 교체 — safe-mode short-circuit을
    # 우회하여 실제 파싱·직렬화 경로를 검증한다.
    fake_drafts = '[{"option": 1, "subject": "테스트 답신", "body": "본문"}]'
    from core.ai import client as ai_client

    monkeypatch.setattr(ai_client, "chat", lambda messages, **k: fake_drafts)

    from cases.case09_ai_email_drafter import scenario
    scenario.run(input_path=case_dir / "input" / "sample_incoming.txt",
                 output_path=case_dir / "output" / "drafts.json")
    text1 = (case_dir / "output" / "drafts.json").read_text(encoding="utf-8")
    scenario.run(input_path=case_dir / "input" / "sample_incoming.txt",
                 output_path=case_dir / "output" / "drafts.json")
    text2 = (case_dir / "output" / "drafts.json").read_text(encoding="utf-8")

    # 두 번째 실행 결과가 첫 번째와 동일 (deterministic)
    assert text1 == text2
    parsed = json.loads(text1)
    assert isinstance(parsed, list)
    assert len(parsed) >= 1
    assert parsed[0]["subject"] == "테스트 답신"


def test_case09_external_apis_listed_in_meta() -> None:
    import yaml
    meta = yaml.safe_load(Path("cases/case09_ai_email_drafter/meta.yaml").read_text())
    assert "openrouter" in meta.get("external_apis", [])
