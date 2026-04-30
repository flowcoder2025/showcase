"""AI 고수준 태스크 — 요약/분류/작성/추출."""
import json
from core.ai import client, prompts


def draft_email(
    incoming_subject: str,
    incoming_body: str,
    company_tone: str,
    history_summary: str,
    *,
    case_id: str | None = None,  # 라이브 실행 시 캐시 저장용
) -> list[dict]:
    """답신 초안 3개 생성. safe fallback 시 빈 리스트 반환.

    case_id가 주어지면 client.chat이 결과를 cases/{case_id}/output/_cached/에
    저장 (시연 deterministic 보장).
    """
    messages = [
        {"role": "system", "content": prompts.EMAIL_DRAFT_SYSTEM},
        {"role": "user", "content": prompts.email_draft_user(
            incoming_subject, incoming_body, company_tone, history_summary
        )},
    ]
    raw = client.chat(messages, case_id=case_id)
    if not raw or "[SAFE-FALLBACK]" in raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []
