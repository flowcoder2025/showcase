"""재사용 프롬프트 템플릿."""

from typing import Any

EMAIL_DRAFT_SYSTEM = """\
당신은 한국 중소기업의 영업 메일을 작성하는 어시스턴트입니다.
주어진 회사 톤·과거 거래 이력에 맞춰 답신 초안 3개를 JSON 배열로 반환하세요.
형식: [{"option": 1, "subject": "...", "body": "..."}, ...]
- option 1: 신중·보수적 톤
- option 2: 친근·관계 강화
- option 3: 명확·간결, 의사결정 빠른 거래처용
"""


def email_draft_user(incoming_subject: str, incoming_body: str, tone: str, history: str) -> str:
    return f"""\
[수신 메일 제목]
{incoming_subject}

[수신 메일 본문]
{incoming_body}

[사내 톤]
{tone}

[과거 거래 요약]
{history}

위 정보를 바탕으로 답신 초안 3개를 JSON 배열로만 반환하세요. 코드블록·설명 금지.
"""


def meeting_summary(
    transcript: str,
    attendees: list[str],
    max_action_items: int,
) -> list[dict[str, Any]]:
    """회의록 요약용 messages 빌드.

    한국어 출력 강제 + JSON schema 명시 + attendees 명단 제약.
    """
    attendee_list = ", ".join(attendees)
    system = (
        "당신은 한국 중소기업의 회의 조력자입니다. "
        "회의록을 읽고 다음 JSON 형식으로 한국어로 응답하세요:\n"
        "{\n"
        '  "summary": "3-5문장 요약",\n'
        '  "action_items": [{"owner": "참석자명", "task": "할 일", "due": "YYYY-MM-DD"}],\n'
        '  "decisions": ["결정 1", "결정 2"]\n'
        "}\n\n"
        "중요: action_items의 owner는 반드시 다음 참석자 명단 안에서만 선택하세요: "
        f"{attendee_list}\n"
        f"action_items는 최대 {max_action_items}개까지.\n"
        "응답은 반드시 valid JSON object로만 반환하세요. 코드블록·설명 금지."
    )
    user = f"참석자: {attendee_list}\n\n회의록:\n{transcript}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
