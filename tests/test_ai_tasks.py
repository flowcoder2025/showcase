from typing import Any

from core.ai import tasks


def test_draft_email_returns_three_options(monkeypatch: Any) -> None:
    def fake_chat(messages: list[dict[str, Any]], **k: Any) -> str:
        return (
            '[{"option": 1, "subject": "s1", "body": "b1"}, '
            '{"option": 2, "subject": "s2", "body": "b2"}, '
            '{"option": 3, "subject": "s3", "body": "b3"}]'
        )

    from core.ai import client

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

    from core.ai import client

    monkeypatch.setattr(client, "chat", fake_safe)

    result = tasks.draft_email("s", "b", "tone", "hist")
    # safe fallback일 때는 빈 리스트 또는 더미 옵션 반환
    assert isinstance(result, list)
