"""case10 — 회의록 AI 요약 + 액션아이템 추출.

Phase 2 Group E. 텍스트 회의록 5건 일괄 → ``core.ai.tasks.summarize_meeting``
으로 요약 + 액션 + 결정사항 추출 → markdown 출력.

음성 입력(whisper)은 Phase 3로 연기 — ``specs/case10-whisper-decision.md``
참조.

scenario는 thin wrapper — safe_mode intercept 경계는 ``runner.py``가 단독으로
관리한다 (T15.5에서 확립한 아키텍처). 자체 wrap 금지.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from core.ai import tasks
from core.common import timer
from core.common.demo_logger import demo_logger

DEFAULT_META_FILENAME = "_meeting_meta.json"
"""파일별 attendees ground truth (owner hallucinate 방지)."""

_DEFAULT_FALLBACK_DIR = Path("personas/sample_data/meeting_transcripts")
"""case input/이 비어 있을 때 사용하는 시드 디렉토리."""


def _load_meta(input_dir: Path) -> dict[str, list[str]]:
    """입력 디렉토리의 ``_meeting_meta.json``에서 파일별 attendees 매핑 로드.

    파일이 없으면 빈 dict 반환 (전체 skip).
    JSON 파싱 실패는 raise — meta 파일이 깨졌다면 fail-loud가 안전하다.
    """
    meta_path = input_dir / DEFAULT_META_FILENAME
    if not meta_path.exists():
        return {}
    data = json.loads(meta_path.read_text(encoding="utf-8"))
    return {entry["filename"]: list(entry["attendees"]) for entry in data}


def _format_markdown(
    meeting_id: str,
    transcript_preview: str,
    summary: tasks.MeetingSummary,
) -> str:
    """``MeetingSummary`` → 보기 좋은 markdown 보고서.

    Args:
        meeting_id: 파일 stem (예: ``m001_monthly_sales``).
        transcript_preview: 회의록 본문 (앞 200자만 사용).
        summary: ``summarize_meeting`` 결과.
    """
    today = date.today().isoformat()
    lines: list[str] = [
        f"# 회의록 요약 — {meeting_id}",
        "",
        f"**작성일**: {today}",
        "",
        "## 요약",
        "",
        summary["summary"] or "_(요약 없음)_",
        "",
        "## 액션 아이템",
        "",
    ]
    if summary["action_items"]:
        lines.append("| 담당자 | 할 일 | 기한 |")
        lines.append("|-------|-------|------|")
        for item in summary["action_items"]:
            due = item["due"] or "-"
            lines.append(f"| {item['owner']} | {item['task']} | {due} |")
    else:
        lines.append("_(추출된 액션 아이템 없음)_")
    lines.append("")
    lines.append("## 결정사항")
    lines.append("")
    if summary["decisions"]:
        for d in summary["decisions"]:
            lines.append(f"- {d}")
    else:
        lines.append("_(추출된 결정사항 없음)_")
    lines.append("")
    lines.append("## 회의록 발췌 (앞 200자)")
    lines.append("")
    lines.append("```")
    lines.append(transcript_preview[:200])
    lines.append("```")
    return "\n".join(lines) + "\n"


def run(
    input_dir: Path | str | None = None,
    output_dir: Path | str | None = None,
) -> dict[str, Any]:
    """회의록 디렉토리 일괄 요약.

    Args:
        input_dir: ``.txt`` + ``_meeting_meta.json``이 있는 디렉토리.
            ``None``이면 ``cases/case10_ai_meeting_summarizer/input``을 시도하고,
            비어있으면 ``personas/sample_data/meeting_transcripts``로 fallback.
        output_dir: markdown 결과 저장 위치.
            ``None``이면 ``cases/case10_ai_meeting_summarizer/output``.

    Returns:
        ``{"processed": int, "errors": int, "files": [...]}``.

        ``files``의 각 항목: ``{"input", "output", "n_actions", "n_decisions"}``.

    Notes:
        ``_underscore`` prefix 파일은 자동 skip (meta JSON 등).
        attendees 미정의 회의는 warning + skip (fail-soft).
        per-meeting ``ValueError``/``OSError``는 격리 — 다른 회의 처리 계속.
    """
    log = demo_logger("case10_ai_meeting_summarizer")
    case_dir = Path(__file__).parent

    # input_dir 결정 — 명시 > case input/ > personas fallback
    if input_dir is None:
        cand = case_dir / "input"
        if not cand.exists() or not list(cand.glob("*.txt")):
            cand = _DEFAULT_FALLBACK_DIR
        in_dir = cand
    else:
        in_dir = Path(input_dir)

    if output_dir is None:
        output_dir = case_dir / "output"
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    meta_map = _load_meta(in_dir)
    transcript_paths = sorted(p for p in in_dir.glob("*.txt") if not p.name.startswith("_"))

    summary_results: dict[str, Any] = {
        "processed": 0,
        "errors": 0,
        "files": [],
    }

    with timer.measure(log, f"회의록 요약 ({len(transcript_paths)}건)", before_minutes=30):
        for tx_path in transcript_paths:
            attendees = meta_map.get(tx_path.name)
            if not attendees:
                log.warning(f"[{tx_path.name}] attendees 미정의 ({DEFAULT_META_FILENAME}) — skip")
                summary_results["errors"] += 1
                continue
            try:
                transcript = tx_path.read_text(encoding="utf-8")
                meeting_summary = tasks.summarize_meeting(
                    transcript,
                    attendees=attendees,
                    case_id="case10_ai_meeting_summarizer",
                )
                md = _format_markdown(tx_path.stem, transcript, meeting_summary)
                out_path = out_dir / f"meeting_summary_{tx_path.stem}.md"
                out_path.write_text(md, encoding="utf-8")
                summary_results["processed"] += 1
                summary_results["files"].append(
                    {
                        "input": tx_path.name,
                        "output": out_path.name,
                        "n_actions": len(meeting_summary["action_items"]),
                        "n_decisions": len(meeting_summary["decisions"]),
                    }
                )
                log.info(
                    f"[{tx_path.name}] 액션 {len(meeting_summary['action_items'])}건 / "
                    f"결정 {len(meeting_summary['decisions'])}건"
                )
            except (ValueError, OSError) as e:
                log.warning(f"[{tx_path.name}] failed: {type(e).__name__}: {e}")
                summary_results["errors"] += 1

    log.success(f"처리 {summary_results['processed']}건 / 실패 {summary_results['errors']}건")
    return summary_results


if __name__ == "__main__":
    run()
