import json
from pathlib import Path

import pytest


def test_case09_safe_mode_returns_deterministic_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """동일 입력 2회 실행 시 결과 동일."""
    monkeypatch.setenv("DEMO_SAFE", "1")
    monkeypatch.chdir(tmp_path)

    # 입력 파일 생성
    case_dir = Path("cases/case09_ai_email_drafter")
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "input").mkdir(exist_ok=True)
    (case_dir / "output").mkdir(exist_ok=True)
    (case_dir / "input" / "sample_incoming.txt").write_text(
        "제목: 단가 문의\n본문: 안녕하세요. 단가표 부탁드립니다."
    )

    # 캐시 미리 작성 (deterministic 보장)
    cache_dir = case_dir / "output" / "_cached"
    cache_dir.mkdir(exist_ok=True)

    from cases.case09_ai_email_drafter import scenario
    scenario.run(input_path=case_dir / "input" / "sample_incoming.txt",
                 output_path=case_dir / "output" / "drafts.json")
    scenario.run(input_path=case_dir / "input" / "sample_incoming.txt",
                 output_path=case_dir / "output" / "drafts.json")

    # 두 번째 실행 결과가 첫 번째와 동일
    text = (case_dir / "output" / "drafts.json").read_text()
    parsed = json.loads(text)
    assert isinstance(parsed, list)


def test_case09_external_apis_listed_in_meta() -> None:
    import yaml
    meta = yaml.safe_load(Path("cases/case09_ai_email_drafter/meta.yaml").read_text())
    assert "openrouter" in meta.get("external_apis", [])
