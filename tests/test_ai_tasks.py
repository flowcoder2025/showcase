import json
from typing import Any

import pytest

from core.ai import client, prompts, tasks


def test_draft_email_returns_three_options(monkeypatch: Any) -> None:
    def fake_chat(messages: list[dict[str, Any]], **k: Any) -> str:
        return (
            '[{"option": 1, "subject": "s1", "body": "b1"}, '
            '{"option": 2, "subject": "s2", "body": "b2"}, '
            '{"option": 3, "subject": "s3", "body": "b3"}]'
        )

    monkeypatch.setattr(client, "chat", fake_chat)

    result = tasks.draft_email(
        incoming_subject="단가 문의",
        incoming_body="안녕하세요. 단가 좀 부탁드립니다.",
        company_tone="친절·정중",
        history_summary="최근 3개월 거래 5건, 평균 50만원",
    )
    assert len(result) == 3
    assert result[0]["subject"] == "s1"


def test_draft_email_handles_safe_fallback(monkeypatch: Any) -> None:
    def fake_safe(messages: list[dict[str, Any]], **k: Any) -> str:
        return "[SAFE-FALLBACK]"

    monkeypatch.setattr(client, "chat", fake_safe)

    result = tasks.draft_email("s", "b", "tone", "hist")
    # safe fallback일 때는 빈 리스트 또는 더미 옵션 반환
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# T12 — summarize_meeting
# ---------------------------------------------------------------------------


_VALID_RESPONSE = json.dumps(
    {
        "summary": "Q3 매출 점검 회의. 3분기 실적 미달 + 4분기 회복 전략 논의.",
        "action_items": [
            {"owner": "박과장", "task": "거래처 단가 재협상", "due": "2026-05-15"},
            {"owner": "이대리", "task": "신규 견적 메일 발송", "due": "2026-05-10"},
        ],
        "decisions": ["4분기 신제품 출시 보류", "마케팅 예산 20% 증액"],
    },
    ensure_ascii=False,
)


def _fake_chat_factory(payload: str) -> Any:
    captured: dict[str, Any] = {}

    def fake_chat(messages: list[dict[str, Any]], **k: Any) -> str:
        captured["messages"] = messages
        captured["kwargs"] = k
        return payload

    fake_chat.captured = captured  # type: ignore[attr-defined]
    return fake_chat


def test_summarize_meeting_returns_typed_summary(monkeypatch: Any) -> None:
    monkeypatch.setattr(client, "chat", _fake_chat_factory(_VALID_RESPONSE))

    result = tasks.summarize_meeting(
        transcript="회의 시작. ...",
        attendees=["김사장", "박과장", "이대리"],
    )
    assert result["summary"].startswith("Q3 매출")
    assert len(result["action_items"]) == 2
    assert result["action_items"][0]["owner"] == "박과장"
    assert result["action_items"][0]["task"] == "거래처 단가 재협상"
    assert result["action_items"][0]["due"] == "2026-05-15"
    assert result["decisions"] == ["4분기 신제품 출시 보류", "마케팅 예산 20% 증액"]


def test_summarize_meeting_drops_owners_not_in_attendees(monkeypatch: Any) -> None:
    """R2-M5: hallucinate된 owner는 raise 대신 drop + warning.

    이전 버전은 ``ValueError`` 였으나 시연 흐름 보호를 위해 부분 손실로 격하했다.
    invalid owner를 가진 action_item만 결과에서 제외되고 valid owner는 통과한다.
    """
    bad_payload = json.dumps(
        {
            "summary": "정상 요약",
            "action_items": [
                {"owner": "이사람없음", "task": "drop", "due": "2026-05-15"},
                {"owner": "김사장", "task": "keep", "due": "2026-05-16"},
            ],
            "decisions": [],
        },
        ensure_ascii=False,
    )
    monkeypatch.setattr(client, "chat", _fake_chat_factory(bad_payload))

    result = tasks.summarize_meeting(
        transcript="회의록 내용",
        attendees=["김사장", "박과장"],
    )
    # invalid owner 항목은 drop, valid owner 항목은 통과.
    assert len(result["action_items"]) == 1
    assert result["action_items"][0]["owner"] == "김사장"
    assert result["action_items"][0]["task"] == "keep"


def test_summarize_meeting_safe_mode_deterministic(monkeypatch: Any) -> None:
    monkeypatch.setenv("DEMO_SAFE", "1")
    transcript = "동일 회의록 내용"
    attendees = ["김사장", "박과장"]

    a = tasks.summarize_meeting(transcript=transcript, attendees=attendees)
    b = tasks.summarize_meeting(transcript=transcript, attendees=attendees)
    assert a == b
    assert "[SAFE-FALLBACK" in a["summary"]


def test_summarize_meeting_safe_mode_uses_first_attendee(monkeypatch: Any) -> None:
    monkeypatch.setenv("DEMO_SAFE", "1")
    result = tasks.summarize_meeting(
        transcript="회의록",
        attendees=["김사장", "박과장", "이대리"],
    )
    assert result["action_items"][0]["owner"] == "김사장"


def test_summarize_meeting_empty_attendees_raises() -> None:
    with pytest.raises(ValueError, match="attendees must not be empty"):
        tasks.summarize_meeting(transcript="회의록", attendees=[])


def test_summarize_meeting_empty_transcript_raises() -> None:
    with pytest.raises(ValueError, match="transcript must not be empty"):
        tasks.summarize_meeting(transcript="", attendees=["김사장"])
    with pytest.raises(ValueError, match="transcript must not be empty"):
        tasks.summarize_meeting(transcript="   \n\t", attendees=["김사장"])


def test_summarize_meeting_invalid_json_returns_empty(monkeypatch: Any) -> None:
    monkeypatch.setattr(client, "chat", _fake_chat_factory("not json {{"))
    result = tasks.summarize_meeting(
        transcript="회의록",
        attendees=["김사장"],
    )
    assert result["summary"] == ""
    assert result["action_items"] == []
    assert result["decisions"] == []


def test_summarize_meeting_chat_returns_safe_fallback_string(monkeypatch: Any) -> None:
    monkeypatch.setattr(client, "chat", _fake_chat_factory("[SAFE-FALLBACK]"))
    result = tasks.summarize_meeting(
        transcript="회의록",
        attendees=["김사장"],
    )
    # safe summary path
    assert "[SAFE-FALLBACK" in result["summary"]
    assert result["action_items"][0]["owner"] == "김사장"


def test_summarize_meeting_response_not_dict_returns_empty(monkeypatch: Any) -> None:
    monkeypatch.setattr(client, "chat", _fake_chat_factory("[1, 2, 3]"))
    result = tasks.summarize_meeting(
        transcript="회의록",
        attendees=["김사장"],
    )
    assert result["summary"] == ""
    assert result["action_items"] == []
    assert result["decisions"] == []


def test_summarize_meeting_truncates_to_max_action_items(monkeypatch: Any) -> None:
    items = [{"owner": "김사장", "task": f"task{i}", "due": "2026-05-15"} for i in range(15)]
    payload = json.dumps(
        {"summary": "s", "action_items": items, "decisions": []},
        ensure_ascii=False,
    )
    monkeypatch.setattr(client, "chat", _fake_chat_factory(payload))

    result = tasks.summarize_meeting(
        transcript="회의록",
        attendees=["김사장"],
        max_action_items=10,
    )
    assert len(result["action_items"]) == 10
    assert result["action_items"][0]["task"] == "task0"
    assert result["action_items"][9]["task"] == "task9"


def test_summarize_meeting_decisions_passthrough(monkeypatch: Any) -> None:
    payload = json.dumps(
        {
            "summary": "s",
            "action_items": [],
            "decisions": ["A", "B"],
        },
        ensure_ascii=False,
    )
    monkeypatch.setattr(client, "chat", _fake_chat_factory(payload))
    result = tasks.summarize_meeting(transcript="회의록", attendees=["김사장"])
    assert result["decisions"] == ["A", "B"]


def test_summarize_meeting_response_format_kwarg_passed(monkeypatch: Any) -> None:
    fake = _fake_chat_factory(_VALID_RESPONSE)
    monkeypatch.setattr(client, "chat", fake)

    tasks.summarize_meeting(
        transcript="회의록",
        attendees=["김사장", "박과장", "이대리"],
    )
    captured = fake.captured
    assert captured["kwargs"]["response_format"] == {"type": "json_object"}


def test_summarize_meeting_case_id_propagated(monkeypatch: Any) -> None:
    fake = _fake_chat_factory(_VALID_RESPONSE)
    monkeypatch.setattr(client, "chat", fake)

    tasks.summarize_meeting(
        transcript="회의록",
        attendees=["김사장", "박과장", "이대리"],
        case_id="case10",
    )
    captured = fake.captured
    assert captured["kwargs"]["case_id"] == "case10"


def test_summarize_meeting_action_items_skip_non_dict(monkeypatch: Any) -> None:
    payload = json.dumps(
        {
            "summary": "s",
            "action_items": [
                "string_not_dict",
                {"owner": "김사장", "task": "ok", "due": "2026-05-15"},
                123,
            ],
            "decisions": [],
        },
        ensure_ascii=False,
    )
    monkeypatch.setattr(client, "chat", _fake_chat_factory(payload))
    result = tasks.summarize_meeting(transcript="회의록", attendees=["김사장"])
    assert len(result["action_items"]) == 1
    assert result["action_items"][0]["owner"] == "김사장"


def test_meeting_summary_prompt_contains_attendees() -> None:
    messages = prompts.meeting_summary("회의록", ["김사장", "박과장"], 10)
    system = next(m["content"] for m in messages if m["role"] == "system")
    assert "김사장" in system
    assert "박과장" in system


def test_meeting_summary_prompt_specifies_korean() -> None:
    messages = prompts.meeting_summary("회의록", ["김사장"], 10)
    system = next(m["content"] for m in messages if m["role"] == "system")
    assert "한국어" in system


def test_meeting_summary_prompt_max_action_items() -> None:
    messages = prompts.meeting_summary("회의록", ["김사장"], 5)
    system = next(m["content"] for m in messages if m["role"] == "system")
    assert "5" in system


def test_safe_summary_deterministic_per_transcript(monkeypatch: Any) -> None:
    monkeypatch.setenv("DEMO_SAFE", "1")
    a1 = tasks.summarize_meeting(transcript="동일", attendees=["김사장"])
    a2 = tasks.summarize_meeting(transcript="동일", attendees=["김사장"])
    b = tasks.summarize_meeting(transcript="다름", attendees=["김사장"])
    assert a1 == a2
    assert a1["summary"] != b["summary"]


# ---------------------------------------------------------------------------
# T12.5 — due format validation + empty action_items/summary warnings
# ---------------------------------------------------------------------------


class _RecordingLogger:
    """info/warning 호출 인자를 캡처하는 minimal logger stub."""

    def __init__(self) -> None:
        self.infos: list[str] = []
        self.warnings: list[str] = []

    def info(self, msg: str) -> None:
        self.infos.append(msg)

    def success(self, msg: str) -> None:  # pragma: no cover - unused
        pass

    def warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def error(self, msg: str) -> None:  # pragma: no cover - unused
        pass


def _patch_summarize_logger(monkeypatch: pytest.MonkeyPatch) -> _RecordingLogger:
    """summarize_meeting 내부의 demo_logger를 RecordingLogger로 교체.

    tasks.py가 ``from ... import demo_logger`` 형태이므로 tasks 모듈에
    바인딩된 이름을 직접 교체해야 한다.
    """
    rec = _RecordingLogger()
    monkeypatch.setattr(tasks, "demo_logger", lambda _case_id: rec)
    return rec


def _payload(
    *,
    summary: str = "회의 요약 정상",
    action_items: list[dict[str, Any]] | None = None,
    decisions: list[str] | None = None,
) -> str:
    return json.dumps(
        {
            "summary": summary,
            "action_items": action_items if action_items is not None else [],
            "decisions": decisions if decisions is not None else [],
        },
        ensure_ascii=False,
    )


def test_summarize_meeting_due_invalid_format_uses_empty(monkeypatch: Any) -> None:
    """due="내일" → fallback to "" + warning."""
    monkeypatch.setattr(
        client,
        "chat",
        _fake_chat_factory(
            _payload(action_items=[{"owner": "김사장", "task": "T", "due": "내일"}])
        ),
    )
    rec = _patch_summarize_logger(monkeypatch)

    result = tasks.summarize_meeting(transcript="회의록", attendees=["김사장"])

    assert result["action_items"][0]["due"] == ""
    assert any("not in YYYY-MM-DD format" in w for w in rec.warnings)


def test_summarize_meeting_due_invalid_date_uses_empty(monkeypatch: Any) -> None:
    """due="2026-13-01" (월 13) → datetime.strptime 실패 → "" + warning."""
    monkeypatch.setattr(
        client,
        "chat",
        _fake_chat_factory(
            _payload(action_items=[{"owner": "김사장", "task": "T", "due": "2026-13-01"}])
        ),
    )
    rec = _patch_summarize_logger(monkeypatch)

    result = tasks.summarize_meeting(transcript="회의록", attendees=["김사장"])

    assert result["action_items"][0]["due"] == ""
    assert any("not a valid date" in w for w in rec.warnings)


def test_summarize_meeting_due_valid_iso_passthrough(monkeypatch: Any) -> None:
    """due="2026-05-08" → 그대로 유지 + warning 없음."""
    monkeypatch.setattr(
        client,
        "chat",
        _fake_chat_factory(
            _payload(action_items=[{"owner": "김사장", "task": "T", "due": "2026-05-08"}])
        ),
    )
    rec = _patch_summarize_logger(monkeypatch)

    result = tasks.summarize_meeting(transcript="회의록", attendees=["김사장"])

    assert result["action_items"][0]["due"] == "2026-05-08"
    assert not any("due" in w for w in rec.warnings)


def test_summarize_meeting_due_empty_string_passthrough(monkeypatch: Any) -> None:
    """due="" → ""  유지 (warning 없음 — empty도 valid)."""
    monkeypatch.setattr(
        client,
        "chat",
        _fake_chat_factory(_payload(action_items=[{"owner": "김사장", "task": "T", "due": ""}])),
    )
    rec = _patch_summarize_logger(monkeypatch)

    result = tasks.summarize_meeting(transcript="회의록", attendees=["김사장"])

    assert result["action_items"][0]["due"] == ""
    assert not any("due" in w for w in rec.warnings)


def test_summarize_meeting_due_extra_whitespace_trimmed(monkeypatch: Any) -> None:
    """due="  2026-05-08  " → strip() 후 "2026-05-08" 유지."""
    monkeypatch.setattr(
        client,
        "chat",
        _fake_chat_factory(
            _payload(action_items=[{"owner": "김사장", "task": "T", "due": "  2026-05-08  "}])
        ),
    )
    rec = _patch_summarize_logger(monkeypatch)

    result = tasks.summarize_meeting(transcript="회의록", attendees=["김사장"])

    assert result["action_items"][0]["due"] == "2026-05-08"
    assert not any("due" in w for w in rec.warnings)


def test_summarize_meeting_empty_action_items_logs_info(monkeypatch: Any) -> None:
    """raw_actions=[] + summary not empty → log.info ("정상 응답")."""
    monkeypatch.setattr(
        client,
        "chat",
        _fake_chat_factory(_payload(summary="요약 OK", action_items=[])),
    )
    rec = _patch_summarize_logger(monkeypatch)

    result = tasks.summarize_meeting(transcript="회의록", attendees=["김사장"])

    assert result["action_items"] == []
    assert any("action_item 없음" in i for i in rec.infos)


def test_summarize_meeting_normalized_to_empty_logs_warning(monkeypatch: Any) -> None:
    """raw_actions에 비-dict만 있어 정규화 후 빈 결과 → log.warning."""
    payload = json.dumps(
        {
            "summary": "요약 OK",
            "action_items": ["string_only", 123],
            "decisions": [],
        },
        ensure_ascii=False,
    )
    monkeypatch.setattr(client, "chat", _fake_chat_factory(payload))
    rec = _patch_summarize_logger(monkeypatch)

    result = tasks.summarize_meeting(transcript="회의록", attendees=["김사장"])

    assert result["action_items"] == []
    assert any("정규화 후 빈 결과" in w for w in rec.warnings)


def test_summarize_meeting_empty_summary_logs_warning(monkeypatch: Any) -> None:
    """summary="" → log.warning ("empty summary")."""
    monkeypatch.setattr(client, "chat", _fake_chat_factory(_payload(summary="")))
    rec = _patch_summarize_logger(monkeypatch)

    result = tasks.summarize_meeting(transcript="회의록", attendees=["김사장"])

    assert result["summary"] == ""
    assert any("empty summary" in w for w in rec.warnings)


def test_summarize_meeting_whitespace_summary_logs_warning(monkeypatch: Any) -> None:
    """summary='   \\n  ' → strip 후 빈 → warning."""
    monkeypatch.setattr(client, "chat", _fake_chat_factory(_payload(summary="   \n  ")))
    rec = _patch_summarize_logger(monkeypatch)

    result = tasks.summarize_meeting(transcript="회의록", attendees=["김사장"])

    assert any("empty summary" in w for w in rec.warnings)
    # raw 값은 그대로 통과 (검증만 — 변형 안 함)
    assert result["summary"] == "   \n  "
