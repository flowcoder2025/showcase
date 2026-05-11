"""case10 — 회의록 AI 요약 + 액션아이템 추출 (T38 ScenarioResult signature)."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

from flowcoder_office_tools.ai import tasks
from flowcoder_office_tools.backends.factory import default_backends, safe_backends
from flowcoder_office_tools.common import timer
from flowcoder_office_tools.common.demo_logger import demo_logger
from flowcoder_office_tools.common.safe_mode_v2 import is_safe
from flowcoder_office_tools.progress import ProgressEvent, done, emit, step
from flowcoder_office_tools.protocols import Backends, ScenarioResult

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_IN = _REPO_ROOT / "personas/sample_data/meeting_transcripts"
_DEFAULT_OUT = Path(__file__).resolve().parent / "output"

DEFAULT_META_FILENAME = "_meeting_meta.json"


def _load_meta(input_dir: Path) -> dict[str, list[str]]:
    """입력 디렉토리의 ``_meeting_meta.json``에서 파일별 attendees 매핑 로드."""
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
    """``MeetingSummary`` → 보기 좋은 markdown 보고서."""
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


def _resolve_input_dir(input_dir: Path | None) -> Path:
    if input_dir is not None:
        return Path(input_dir)
    case_dir = Path(__file__).resolve().parent
    cand = case_dir / "input"
    if cand.exists() and list(cand.glob("*.txt")):
        return cand
    return _DEFAULT_IN


def run(
    *,
    input_dir: Path | None = None,
    output_dir: Path | None = None,
    backends: Backends | None = None,
    progress_cb: Callable[[ProgressEvent], None] | None = None,
    config: dict[str, Any] | None = None,
) -> ScenarioResult:
    """회의록 디렉토리 일괄 요약."""
    out_dir = Path(output_dir) if output_dir else _DEFAULT_OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    _ = backends or (safe_backends() if is_safe() else default_backends())  # T40 wire-up
    _ = config or {}
    in_dir = _resolve_input_dir(input_dir)

    log = demo_logger("case10_ai_meeting_summarizer")
    meta_map = _load_meta(in_dir)
    transcript_paths = sorted(p for p in in_dir.glob("*.txt") if not p.name.startswith("_"))

    processed = 0
    errors = 0
    files_meta: list[dict[str, Any]] = []
    output_files: list[Path] = []
    summaries_extra: list[dict[str, Any]] = []

    total_files = len(transcript_paths)
    with timer.measure(log, f"회의록 요약 ({total_files}건)", before_minutes=30):
        for idx, tx_path in enumerate(transcript_paths, start=1):
            emit(progress_cb, step("case10", tx_path.name, idx, total_files))
            attendees = meta_map.get(tx_path.name)
            if not attendees:
                log.warning(f"[{tx_path.name}] attendees 미정의 ({DEFAULT_META_FILENAME}) — skip")
                errors += 1
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
                processed += 1
                output_files.append(out_path)
                files_meta.append(
                    {
                        "input": tx_path.name,
                        "output": out_path.name,
                        "n_actions": len(meeting_summary["action_items"]),
                        "n_decisions": len(meeting_summary["decisions"]),
                    }
                )
                summaries_extra.append(
                    {"meeting_id": tx_path.stem, "summary": dict(meeting_summary)}
                )
                log.info(
                    f"[{tx_path.name}] 액션 {len(meeting_summary['action_items'])}건 / "
                    f"결정 {len(meeting_summary['decisions'])}건"
                )
            except (ValueError, OSError) as e:
                log.warning(f"[{tx_path.name}] failed: {type(e).__name__}: {e}")
                errors += 1

    log.success(f"처리 {processed}건 / 실패 {errors}건")
    emit(progress_cb, done("case10", f"요약 {processed}건"))
    return {
        "case_id": "case10",
        "summary_text": f"회의록 {processed}건 요약 / 실패 {errors}건",
        "output_files": output_files,
        "metrics": {"processed": processed, "errors": errors},
        "failures": [],
        "extras": {"files": files_meta, "summaries": summaries_extra},
    }


if __name__ == "__main__":
    run()
