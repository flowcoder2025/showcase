"""AI 고수준 태스크 — 요약/분류/작성/추출."""

import hashlib
import json
import re
from datetime import datetime
from typing import Any, TypedDict, cast

from core.ai import client, prompts
from core.common.demo_logger import Logger, demo_logger

_ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _normalize_due(value: Any, log: Logger) -> str:
    """due 형식 검증. YYYY-MM-DD만 허용. 잘못된 형식 → "" fallback + warning.

    빈 문자열은 valid (LLM이 due를 모를 수도 있음 — graceful).
    """
    s = str(value).strip()
    if not s:
        return ""
    if not _ISO_DATE_PATTERN.match(s):
        log.warning(f"due not in YYYY-MM-DD format: {value!r}, using ''")
        return ""
    try:
        datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        log.warning(f"due is not a valid date: {value!r}, using ''")
        return ""
    return s


def draft_email(
    incoming_subject: str,
    incoming_body: str,
    company_tone: str,
    history_summary: str,
    *,
    case_id: str | None = None,  # 라이브 실행 시 캐시 저장용
) -> list[dict[str, Any]]:
    """답신 초안 3개 생성. safe fallback 시 빈 리스트 반환.

    case_id가 주어지면 client.chat이 결과를 cases/{case_id}/output/_cached/에
    저장 (시연 deterministic 보장).
    """
    messages = [
        {"role": "system", "content": prompts.EMAIL_DRAFT_SYSTEM},
        {
            "role": "user",
            "content": prompts.email_draft_user(
                incoming_subject, incoming_body, company_tone, history_summary
            ),
        },
    ]
    log = demo_logger(case_id or "tasks")
    raw = client.chat(messages, case_id=case_id)
    if not raw or "[SAFE-FALLBACK]" in raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        log.warning(f"draft_email: invalid JSON from AI ({e}); raw[:80]={raw[:80]!r}")
        return []
    if not isinstance(parsed, list):
        log.warning(f"draft_email: AI returned non-list ({type(parsed).__name__}); skipping")
        return []
    return cast(list[dict[str, Any]], parsed)


# ---------------------------------------------------------------------------
# T12 — summarize_meeting (case10)
# ---------------------------------------------------------------------------


class ActionItem(TypedDict):
    owner: str
    task: str
    due: str  # YYYY-MM-DD


class MeetingSummary(TypedDict):
    summary: str
    action_items: list[ActionItem]
    decisions: list[str]


def summarize_meeting(
    transcript: str,
    *,
    attendees: list[str],
    max_action_items: int = 10,
    case_id: str | None = None,
) -> MeetingSummary:
    """회의록 → 요약 + 액션아이템 + 결정사항.

    Args:
        transcript: 회의록 본문 (한국어)
        attendees: 참석자 명단. action_items의 owner는 이 목록 안에서만 허용
        max_action_items: 결과에 포함할 최대 액션아이템 수 (LLM 응답을 truncate)
        case_id: safe_mode 캐시 키 (라이브 실행 시 deterministic 캐시)

    Raises:
        ValueError: attendees가 빈 리스트인 경우.
        ValueError: transcript가 비어있거나 whitespace-only인 경우.

    Returns:
        성공: MeetingSummary (summary/action_items/decisions).
        safe-mode: deterministic dummy MeetingSummary (transcript hash 기반).
        JSON parse 실패 또는 비-dict 응답: 빈 결과 + warning log
            (case09 draft_email 패턴 일관).

    Note:
        R2-M5 — LLM 응답의 ``action_item.owner`` 가 ``attendees`` 에 없는
        경우 (hallucinate)는 raise 대신 해당 항목만 drop + WARNING 로그를
        남긴다. 시연 흐름을 끊지 않고 "한 회의의 부분 손실"로 격하한다.
        (이전 버전은 ``ValueError`` 였음.)
    """
    if not attendees:
        raise ValueError("attendees must not be empty")
    if not transcript or not transcript.strip():
        raise ValueError("transcript must not be empty")

    # safe-mode short-circuit (chat()도 동일하게 short-circuit하지만
    # owner 검증/json 처리 비용을 아끼고 deterministic 출력을 보장).
    from core.common import safe_mode

    if safe_mode.is_safe():
        return _safe_summary(transcript, attendees)

    messages = prompts.meeting_summary(transcript, attendees, max_action_items)
    response_str = client.chat(
        messages,
        case_id=case_id,
        response_format={"type": "json_object"},
    )

    # chat() 자체가 force_safe로 fallback했을 수 있음.
    # R2-M4: 첫 비교는 두 번째 substring 검사에 흡수되므로 중복 — 단일 체크로 단순화.
    if "[SAFE-FALLBACK]" in response_str:
        return _safe_summary(transcript, attendees)

    log = demo_logger("summarize_meeting")
    try:
        parsed = json.loads(response_str)
    except json.JSONDecodeError as e:
        log.warning(
            f"summarize_meeting: invalid JSON from AI ({e}); raw[:80]={response_str[:80]!r}"
        )
        return MeetingSummary(summary="", action_items=[], decisions=[])

    if not isinstance(parsed, dict):
        log.warning(f"summarize_meeting: AI returned non-dict ({type(parsed).__name__}); skipping")
        return MeetingSummary(summary="", action_items=[], decisions=[])

    raw_actions_obj = parsed.get("action_items", [])
    raw_actions: list[Any] = raw_actions_obj if isinstance(raw_actions_obj, list) else []

    # owner hallucinate 처리 (R2-M5) — LLM이 attendees 외 사람을 배정하면
    # 해당 항목만 drop + WARNING 로그. raise하지 않아 시연 흐름을 보호한다.
    valid_actions: list[dict[str, Any]] = []
    invalid_owners: list[Any] = []
    for item in raw_actions:
        if not isinstance(item, dict):
            continue
        if item.get("owner") not in attendees:
            invalid_owners.append(item.get("owner"))
            continue
        valid_actions.append(item)
    if invalid_owners:
        log.warning(
            f"action_item owners not in attendees (dropped {len(invalid_owners)}): "
            f"{invalid_owners}; attendees={attendees}"
        )

    action_items: list[ActionItem] = []
    for item in valid_actions[:max_action_items]:
        action_items.append(
            ActionItem(
                owner=str(item.get("owner", "")),
                task=str(item.get("task", "")),
                due=_normalize_due(item.get("due", ""), log),
            )
        )

    # 빈 action_items 분기 — 시연 시 "정상 응답인지 응답 오류인지" 구분
    if not action_items:
        if not raw_actions:
            log.info("회의에서 추출된 action_item 없음 (정상 응답)")
        else:
            log.warning(f"raw_actions 있지만 정규화 후 빈 결과: {raw_actions!r}")

    summary_str = str(parsed.get("summary", ""))
    if not summary_str.strip():
        log.warning(f"LLM returned empty summary; raw response: {response_str[:200]!r}")

    decisions_raw = parsed.get("decisions", [])
    decisions: list[str] = (
        [str(d) for d in decisions_raw] if isinstance(decisions_raw, list) else []
    )

    return MeetingSummary(
        summary=summary_str,
        action_items=action_items,
        decisions=decisions,
    )


def _safe_summary(transcript: str, attendees: list[str]) -> MeetingSummary:
    """deterministic dummy — transcript hash 기반.

    동일 transcript는 동일 결과, 다른 transcript는 다른 hash로 구분 가능
    (시연 시 reproducibility 확인용).
    """
    h = hashlib.sha1(transcript.encode("utf-8")).hexdigest()[:8]
    return MeetingSummary(
        summary=f"[SAFE-FALLBACK 더미 요약 {h}]",
        action_items=[
            ActionItem(
                owner=attendees[0],
                task="[safe] 액션아이템 더미",
                due="2026-05-08",
            ),
        ],
        decisions=["[safe] 결정사항 더미"],
    )
