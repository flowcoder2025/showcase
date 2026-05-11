"""Phase 2 DoD verification — AI cases (case09/case10).

Integration-level checks that complement (not replace) the per-case tests in
``tests/test_case09.py`` and ``tests/test_case10_meeting_summarizer.py``.

DoD criteria (per ``specs/2026-05-01-phase2-plan.md`` lines 1926-1947):

- case09: safe_mode deterministic, 3안 반환, OpenRouter 폴백 체인 잠금.
- case10: owner hallucinate 보호 (fail-loud), MeetingSummary TypedDict shape,
  whisper deferral 결정 문서 잠금, safe-mode dict shape.

All tests run with mocks/stubs — no real OpenRouter calls.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from cases.case09_ai_email_drafter import scenario as case09_scenario
from cases.case10_ai_meeting_summarizer import scenario as case10_scenario
from core.ai import client as ai_client
from core.ai import tasks
from core.ai.tasks import ActionItem, MeetingSummary

DEFAULT_ATTENDEES = ["김사장", "이대리", "박과장"]


# --- shared helpers --------------------------------------------------------


_CASE09_INCOMING = "제목: 단가 인하 요청\n본문: 안녕하세요. 단가 5% 인하 검토 부탁드립니다."


def _seed_case09_input(tmp_path: Path) -> tuple[str, Path]:
    """case09 입력 (config["incoming_message"]) + 출력 디렉토리 반환."""
    out_dir = tmp_path / "case09_out"
    return _CASE09_INCOMING, out_dir


def _seed_case10_input(tmp_path: Path, *, n: int = 2) -> Path:
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    files: list[dict[str, object]] = []
    for i in range(n):
        name = f"m{i:03d}.txt"
        (in_dir / name).write_text(f"회의록 본문 {i}", encoding="utf-8")
        files.append({"filename": name, "attendees": DEFAULT_ATTENDEES})
    (in_dir / case10_scenario.DEFAULT_META_FILENAME).write_text(
        json.dumps(files, ensure_ascii=False), encoding="utf-8"
    )
    return in_dir


# --- case09 DoD: safe_mode deterministic ----------------------------------


def test_case09_safe_mode_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """DoD: 동일 입력으로 2회 실행 시 결과 byte-identical (Phase 1 invariant lock).

    safe-mode short-circuit + deterministic fake AI 응답으로 ``[SAFE-FALLBACK]``
    경로 우회 → 실제 직렬화/파싱이 reproducible 함을 검증.
    """
    monkeypatch.setenv("DEMO_SAFE", "1")
    incoming, _ = _seed_case09_input(tmp_path)

    fake_drafts = json.dumps(
        [
            {"option": 1, "subject": "답신 A", "body": "본문 A"},
            {"option": 2, "subject": "답신 B", "body": "본문 B"},
            {"option": 3, "subject": "답신 C", "body": "본문 C"},
        ],
        ensure_ascii=False,
    )
    monkeypatch.setattr(ai_client, "chat", lambda messages, **k: fake_drafts)

    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"
    r1 = case09_scenario.run(output_dir=out1, config={"incoming_message": incoming})
    r2 = case09_scenario.run(output_dir=out2, config={"incoming_message": incoming})
    text1 = r1["output_files"][0].read_text(encoding="utf-8")
    text2 = r2["output_files"][0].read_text(encoding="utf-8")

    assert text1 == text2, "DoD gap: case09 not deterministic across re-runs"


def test_case09_returns_three_drafts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """DoD: case09는 3안의 답신 초안을 반환 (meta.yaml '3안 비교' 약속)."""
    monkeypatch.setenv("DEMO_SAFE", "1")
    incoming, out_dir = _seed_case09_input(tmp_path)

    fake_drafts = json.dumps(
        [
            {"option": 1, "subject": "강한 톤", "body": "단가 인하 어렵습니다"},
            {"option": 2, "subject": "중립 톤", "body": "검토 후 회신드립니다"},
            {"option": 3, "subject": "유연 톤", "body": "조건 협의 가능합니다"},
        ],
        ensure_ascii=False,
    )
    monkeypatch.setattr(ai_client, "chat", lambda messages, **k: fake_drafts)

    result = case09_scenario.run(output_dir=out_dir, config={"incoming_message": incoming})
    parsed = json.loads(result["output_files"][0].read_text(encoding="utf-8"))

    assert isinstance(parsed, list)
    assert len(parsed) == 3, f"DoD gap: expected 3 drafts, got {len(parsed)}"
    for draft in parsed:
        assert "subject" in draft
        assert "body" in draft


def test_case09_uses_openrouter_fallback_chain() -> None:
    """DoD: ``MODEL_PRIORITY`` 가 문서화된 폴백 체인을 유지한다.

    Gemini 2.5 Flash → Claude Haiku 4.5 → GPT-4o-mini 순서. 본 테스트는 R3-H1
    invariant — 모델 우선순위가 silent 변경되지 않도록 잠근다.
    """
    expected_chain: tuple[str, ...] = (
        "google/gemini-2.5-flash",
        "anthropic/claude-haiku-4-5",
        "openai/gpt-4o-mini",
    )
    assert ai_client.MODEL_PRIORITY == expected_chain, (
        f"DoD gap: MODEL_PRIORITY drift — got {ai_client.MODEL_PRIORITY!r}, "
        f"expected {expected_chain!r}"
    )


# --- case10 DoD: owner hallucinate 보호 -----------------------------------


def test_case10_owner_hallucinate_protection(monkeypatch: pytest.MonkeyPatch) -> None:
    """DoD: ``summarize_meeting`` 이 attendees 외 owner를 받으면 해당 항목을 drop.

    R2-M5 (T25 update) — LLM이 참석자 명단에 없는 사람을 action_item.owner로
    hallucinate 하면 raise 대신 해당 항목만 drop + WARNING 로그를 남긴다.
    시연 흐름을 끊지 않고 "한 회의의 부분 손실" 로 격하한다 (이전: ValueError).
    """
    # safe-mode short-circuit 우회 (deterministic dummy 가 아닌 검증 로직 통과)
    monkeypatch.delenv("DEMO_SAFE", raising=False)
    from core.common import safe_mode

    monkeypatch.setattr(safe_mode, "is_safe", lambda: False)

    # LLM이 attendees 외 owner를 응답하는 시나리오 시뮬레이션 — 모두 invalid 한 케이스.
    bad_response = json.dumps(
        {
            "summary": "요약",
            "action_items": [
                {"owner": "유령직원", "task": "할 일", "due": "2026-05-10"},
            ],
            "decisions": ["결정"],
        },
        ensure_ascii=False,
    )
    monkeypatch.setattr(ai_client, "chat", lambda messages, **k: bad_response)

    result = tasks.summarize_meeting(
        "회의록 본문",
        attendees=["김사장", "이대리"],
    )
    # invalid owner 항목은 결과에서 제외되어야 한다.
    assert result["action_items"] == []
    # summary/decisions 는 그대로 보존.
    assert result["summary"] == "요약"
    assert result["decisions"] == ["결정"]


def test_case10_action_items_typed_dict_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    """DoD: ``MeetingSummary`` 반환 타입의 shape — summary/action_items/decisions."""
    monkeypatch.delenv("DEMO_SAFE", raising=False)
    from core.common import safe_mode

    monkeypatch.setattr(safe_mode, "is_safe", lambda: False)

    response = json.dumps(
        {
            "summary": "5월 매출 점검",
            "action_items": [
                {"owner": "김사장", "task": "예산 승인", "due": "2026-05-15"},
                {"owner": "이대리", "task": "보고서 작성", "due": "2026-05-12"},
            ],
            "decisions": ["목표 9억 확정", "회의 격주"],
        },
        ensure_ascii=False,
    )
    monkeypatch.setattr(ai_client, "chat", lambda messages, **k: response)

    result = tasks.summarize_meeting("본문", attendees=DEFAULT_ATTENDEES)

    # MeetingSummary keys + types
    assert set(result.keys()) == {"summary", "action_items", "decisions"}
    assert isinstance(result["summary"], str)
    assert isinstance(result["action_items"], list)
    assert isinstance(result["decisions"], list)

    assert result["summary"] == "5월 매출 점검"
    assert len(result["action_items"]) == 2
    assert len(result["decisions"]) == 2

    # ActionItem shape per item
    for item in result["action_items"]:
        assert set(item.keys()) == {"owner", "task", "due"}
        assert isinstance(item["owner"], str)
        assert isinstance(item["task"], str)
        assert isinstance(item["due"], str)
        # YYYY-MM-DD format (or empty string if invalid)
        if item["due"]:
            assert len(item["due"]) == 10
            assert item["due"][4] == "-"
            assert item["due"][7] == "-"

    # decisions are strings
    for d in result["decisions"]:
        assert isinstance(d, str)


def test_case10_whisper_deferral_marker() -> None:
    """DoD: ``specs/case10-whisper-decision.md`` 가 존재하고 Phase 3 deferral을 명시.

    T22 ``dod-n6-decision.md`` 패턴 mirror — 명시적 deviation 결정이 spec 안에
    잠겨야 한다.
    """
    decision_path = Path("specs/case10-whisper-decision.md")
    assert decision_path.exists(), (
        f"DoD gap: whisper deferral decision doc missing at {decision_path}"
    )
    content = decision_path.read_text(encoding="utf-8")
    # 핵심 키워드 — 결정의 본질
    assert "Phase 3" in content, "DoD gap: 'Phase 3' deferral not stated"
    assert "연기" in content or "deferred" in content.lower() or "보류" in content, (
        "DoD gap: deferral language not present"
    )
    assert "whisper" in content.lower(), "DoD gap: whisper not referenced"


def test_case10_safe_mode_returns_scenario_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DoD: case10 safe-mode 실행 시 ScenarioResult shape 안정 (T38)."""
    monkeypatch.setenv("DEMO_SAFE", "1")
    in_dir = _seed_case10_input(tmp_path, n=2)
    out_dir = tmp_path / "out"

    result: dict[str, Any] = case10_scenario.run(input_dir=in_dir, output_dir=out_dir)

    assert set(result.keys()) == {
        "case_id",
        "summary_text",
        "output_files",
        "metrics",
        "failures",
        "extras",
    }
    assert result["case_id"] == "case10"
    assert isinstance(result["metrics"]["processed"], int)
    assert isinstance(result["metrics"]["errors"], int)
    assert result["metrics"]["processed"] == 2
    assert result["metrics"]["errors"] == 0

    files = result["extras"]["files"]
    assert isinstance(files, list)
    assert len(files) == 2
    for entry in files:
        assert "input" in entry
        assert "output" in entry
        assert isinstance(entry["n_actions"], int)
        assert isinstance(entry["n_decisions"], int)


# --- ergonomics: ActionItem/MeetingSummary import surface ----------------


def test_case10_typed_dicts_exported() -> None:
    """DoD: ``ActionItem`` 과 ``MeetingSummary`` 가 ``core.ai.tasks`` 에서 import 가능.

    외부 호출자(다음 컨설팅 프로젝트)가 타입을 import 할 수 있도록 잠근다.
    """
    # 두 TypedDict가 import 가능 + 인스턴스 생성 가능
    item: ActionItem = ActionItem(owner="김사장", task="할일", due="2026-05-10")
    summary: MeetingSummary = MeetingSummary(
        summary="요약",
        action_items=[item],
        decisions=["결정"],
    )
    # 런타임 표현은 dict (TypedDict는 dict의 alias)
    assert isinstance(item, dict)
    assert isinstance(summary, dict)
    assert summary["action_items"][0]["owner"] == "김사장"
