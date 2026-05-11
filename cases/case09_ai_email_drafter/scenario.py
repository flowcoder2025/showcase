"""Case 09 — AI 메일 초안 생성 (T38: config["incoming_message"] 텍스트 입력 + ScenarioResult)."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from cases._protocols import Backends, ScenarioResult
from core.ai import tasks
from core.backends.factory import default_backends, safe_backends
from core.common import timer
from core.common.demo_logger import demo_logger
from core.common.safe_mode_v2 import is_safe
from core.progress import ProgressEvent

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_OUT = Path(__file__).resolve().parent / "output"
_DEFAULT_INPUT_FILE = Path(__file__).resolve().parent / "input" / "sample_incoming.txt"

COMPANY_TONE = (
    "친절·정중, 결정 전 데이터 확인을 명시. 가격 인하 요청에는 즉답 회피하고 회의 후 답신 약속."
)
HISTORY_SUMMARY = "최근 6개월 거래 12건 / 평균 단가 50,000원 / 최근 인하 이력 없음 / 회수 양호"


def _resolve_incoming(config: dict[str, Any]) -> str:
    """config["incoming_message"] 우선 → 디스크 sample 파일 fallback."""
    explicit = config.get("incoming_message")
    if isinstance(explicit, str) and explicit.strip():
        return explicit
    return _DEFAULT_INPUT_FILE.read_text(encoding="utf-8")


def run(
    *,
    input_dir: Path | None = None,
    output_dir: Path | None = None,
    backends: Backends | None = None,
    progress_cb: Callable[[ProgressEvent], None] | None = None,
    config: dict[str, Any] | None = None,
) -> ScenarioResult:
    """수신 메일 텍스트 → AI 메일 초안 3안 생성. input_dir은 ignored (text input via config)."""
    out_dir = Path(output_dir) if output_dir else _DEFAULT_OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    _ = backends or (safe_backends() if is_safe() else default_backends())  # T40 wire-up
    cfg = config or {}
    incoming = _resolve_incoming(cfg)

    log = demo_logger("case09")
    subject_line, _sep, body = incoming.partition("\n")
    subject = subject_line.replace("제목:", "").strip()
    body = body.lstrip("본문:").strip()

    with timer.measure(log, "AI 메일 초안 3안 생성", before_minutes=10):
        drafts = tasks.draft_email(
            incoming_subject=subject,
            incoming_body=body,
            company_tone=COMPANY_TONE,
            history_summary=HISTORY_SUMMARY,
            case_id="case09_ai_email_drafter",
        )

    output_path = out_dir / "drafts.json"
    output_path.write_text(json.dumps(drafts, ensure_ascii=False, indent=2), encoding="utf-8")
    log.success(f"초안 {len(drafts)}건 저장 → {output_path}")

    return {
        "case_id": "case09",
        "summary_text": f"AI 메일 초안 {len(drafts)}건 생성 → {output_path.name}",
        "output_files": [output_path],
        "metrics": {"drafts": len(drafts)},
        "failures": [],
        "extras": {"drafts": drafts, "subject": subject},
    }


if __name__ == "__main__":
    run()
