"""Case 09 — AI 메일 초안 생성 (사내 톤 + 거래 이력)."""
import json
from pathlib import Path

from core.ai import tasks
from core.common import timer
from core.common.demo_logger import demo_logger

COMPANY_TONE = (
    "친절·정중, 결정 전 데이터 확인을 명시. "
    "가격 인하 요청에는 즉답 회피하고 회의 후 답신 약속."
)

# 시연용 가상 거래 이력 (실제론 personas/sample_data에서 조회)
HISTORY_SUMMARY = "최근 6개월 거래 12건 / 평균 단가 50,000원 / 최근 인하 이력 없음 / 회수 양호"


def run(input_path: Path | str = "cases/case09_ai_email_drafter/input/sample_incoming.txt",
        output_path: Path | str = "cases/case09_ai_email_drafter/output/drafts.json") -> int:
    log = demo_logger("case09")
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    incoming = input_path.read_text(encoding="utf-8")
    subject_line, _, body = incoming.partition("\n")
    subject = subject_line.replace("제목:", "").strip()
    body = body.lstrip("본문:").strip()

    with timer.measure(log, "AI 메일 초안 3안 생성", before_minutes=10):
        drafts = tasks.draft_email(
            incoming_subject=subject,
            incoming_body=body,
            company_tone=COMPANY_TONE,
            history_summary=HISTORY_SUMMARY,
            case_id="case09_ai_email_drafter",  # 캐시 저장용 (deterministic 시연)
        )

    output_path.write_text(
        json.dumps(drafts, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.success(f"초안 {len(drafts)}건 저장 → {output_path}")
    return 0


if __name__ == "__main__":
    run()
