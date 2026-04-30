"""재사용 프롬프트 템플릿."""

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
