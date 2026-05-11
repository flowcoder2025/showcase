"""T13: case10 — 회의록 AI 요약 시나리오.

``core.ai.tasks.summarize_meeting`` mock 기반 contract 검증. 실제 OpenRouter
호출 없음.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import pytest

from cases.case10_ai_meeting_summarizer import scenario
from core.ai import tasks
from core.ai.tasks import ActionItem, MeetingSummary

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

DEFAULT_ATTENDEES = ["김사장", "이대리", "박과장"]


def _seed_input(
    tmp_path: Path,
    *,
    n: int = 3,
    extra_files: dict[str, str] | None = None,
    meta: list[dict[str, object]] | None = None,
) -> Path:
    """입력 디렉토리 생성 — n개 .txt + meta JSON.

    ``extra_files``는 추가로 (특히 underscore prefix 검증용) 만들 파일.
    ``meta``를 ``None``으로 두면 기본 5건 attendees ground truth가 자동 주입.
    """
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    files: list[dict[str, object]] = []
    for i in range(n):
        name = f"m{i:03d}.txt"
        (in_dir / name).write_text(f"회의록 본문 {i}", encoding="utf-8")
        files.append({"filename": name, "attendees": DEFAULT_ATTENDEES})
    if extra_files:
        for name, content in extra_files.items():
            (in_dir / name).write_text(content, encoding="utf-8")
    meta_payload = meta if meta is not None else files
    (in_dir / scenario.DEFAULT_META_FILENAME).write_text(
        json.dumps(meta_payload, ensure_ascii=False),
        encoding="utf-8",
    )
    return in_dir


def _mock_summarize(
    monkeypatch: pytest.MonkeyPatch,
    response: MeetingSummary | None = None,
    fail_filenames: tuple[str, ...] = (),
    capture_calls: list[dict[str, object]] | None = None,
) -> None:
    """``tasks.summarize_meeting`` 패치 — fail_filenames는 ValueError raise.

    ``capture_calls``를 주면 호출 인자 (transcript/attendees) 기록.
    """
    default: MeetingSummary = response or MeetingSummary(
        summary="가상 회의 요약입니다.",
        action_items=[
            ActionItem(owner="김사장", task="결정 1", due="2026-05-10"),
            ActionItem(owner="이대리", task="결정 2", due="2026-05-15"),
        ],
        decisions=["5월 매출 목표 9억 확정"],
    )

    def _fake(transcript: str, *, attendees: list[str], **_: object) -> MeetingSummary:
        if capture_calls is not None:
            capture_calls.append({"transcript": transcript, "attendees": list(attendees)})
        # transcript 본문에 fail 토큰을 삽입한 회의는 ValueError raise
        for token in fail_filenames:
            if token in transcript:
                raise ValueError(f"mock summarize failure for {token}")
        return default

    monkeypatch.setattr(tasks, "summarize_meeting", _fake)


# ---------------------------------------------------------------------------
# 1. 기본 처리
# ---------------------------------------------------------------------------


def test_run_processes_all_transcripts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    in_dir = _seed_input(tmp_path, n=5)
    _mock_summarize(monkeypatch)
    out_dir = tmp_path / "out"

    result = scenario.run(input_dir=in_dir, output_dir=out_dir)

    assert result["metrics"]["processed"] == 5
    assert result["metrics"]["errors"] == 0
    md_files = sorted(out_dir.glob("meeting_summary_*.md"))
    assert len(md_files) == 5


# ---------------------------------------------------------------------------
# 2. attendees 미정의 → skip
# ---------------------------------------------------------------------------


def test_run_missing_attendees_meta_skips_with_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    # .txt 있지만 meta JSON 없음
    (in_dir / "m000.txt").write_text("내용", encoding="utf-8")
    (in_dir / "m001.txt").write_text("내용", encoding="utf-8")

    _mock_summarize(monkeypatch)
    out_dir = tmp_path / "out"
    result = scenario.run(input_dir=in_dir, output_dir=out_dir)

    assert result["metrics"]["processed"] == 0
    assert result["metrics"]["errors"] == 2  # 2건 모두 skip → errors 카운트


# ---------------------------------------------------------------------------
# 3. personas fallback
# ---------------------------------------------------------------------------


def test_run_uses_personas_fallback_when_input_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """case input/ 비어있으면 personas seed 디렉토리 사용."""
    seed_dir = tmp_path / "personas_seed"
    seed_dir.mkdir()
    for i in range(5):
        (seed_dir / f"m{i:03d}.txt").write_text(f"본문 {i}", encoding="utf-8")
    meta = [{"filename": f"m{i:03d}.txt", "attendees": DEFAULT_ATTENDEES} for i in range(5)]
    (seed_dir / scenario.DEFAULT_META_FILENAME).write_text(json.dumps(meta), encoding="utf-8")

    monkeypatch.setattr(scenario, "_DEFAULT_IN", seed_dir)

    _mock_summarize(monkeypatch)
    out_dir = tmp_path / "out"
    result = scenario.run(input_dir=None, output_dir=out_dir)

    assert result["metrics"]["processed"] == 5


# ---------------------------------------------------------------------------
# 4. per-meeting 실패 격리
# ---------------------------------------------------------------------------


def test_run_continues_after_per_meeting_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    files: list[dict[str, object]] = []
    for i in range(4):
        name = f"m{i:03d}.txt"
        # 본문에 식별 토큰 삽입 → mock에서 fail 판정
        (in_dir / name).write_text(f"본문 token_{i}", encoding="utf-8")
        files.append({"filename": name, "attendees": DEFAULT_ATTENDEES})
    (in_dir / scenario.DEFAULT_META_FILENAME).write_text(json.dumps(files), encoding="utf-8")

    _mock_summarize(monkeypatch, fail_filenames=("token_1", "token_3"))
    out_dir = tmp_path / "out"
    result = scenario.run(input_dir=in_dir, output_dir=out_dir)

    assert result["metrics"]["processed"] == 2
    assert result["metrics"]["errors"] == 2


# ---------------------------------------------------------------------------
# 5. safe-mode (mock으로 SAFE-FALLBACK 응답 시뮬레이션)
# ---------------------------------------------------------------------------


def test_run_safe_mode_uses_dummy_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """summarize_meeting이 SAFE-FALLBACK 표기 응답 → markdown에 그대로 포함."""
    safe_response = MeetingSummary(
        summary="[SAFE-FALLBACK 더미 요약 abc12345]",
        action_items=[
            ActionItem(owner="김사장", task="[safe] 액션", due="2026-05-08"),
        ],
        decisions=["[safe] 결정사항 더미"],
    )
    in_dir = _seed_input(tmp_path, n=2)
    _mock_summarize(monkeypatch, response=safe_response)

    out_dir = tmp_path / "out"
    result = scenario.run(input_dir=in_dir, output_dir=out_dir)

    assert result["metrics"]["processed"] == 2
    md = (out_dir / "meeting_summary_m000.md").read_text(encoding="utf-8")
    assert "[SAFE-FALLBACK" in md
    assert "[safe] 결정사항 더미" in md


# ---------------------------------------------------------------------------
# 6. 출력 markdown 구조
# ---------------------------------------------------------------------------


def test_run_output_markdown_format(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    in_dir = _seed_input(tmp_path, n=1)
    _mock_summarize(monkeypatch)
    out_dir = tmp_path / "out"
    scenario.run(input_dir=in_dir, output_dir=out_dir)

    md = (out_dir / "meeting_summary_m000.md").read_text(encoding="utf-8")
    assert "# 회의록 요약" in md
    assert "## 요약" in md
    assert "## 액션 아이템" in md
    assert "## 결정사항" in md


# ---------------------------------------------------------------------------
# 7. 액션 아이템 표 형식
# ---------------------------------------------------------------------------


def test_run_action_items_table_format(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    response = MeetingSummary(
        summary="요약",
        action_items=[
            ActionItem(owner="김사장", task="A", due="2026-05-10"),
            ActionItem(owner="이대리", task="B", due="2026-05-12"),
            ActionItem(owner="박과장", task="C", due="2026-05-14"),
        ],
        decisions=["결정"],
    )
    in_dir = _seed_input(tmp_path, n=1)
    _mock_summarize(monkeypatch, response=response)
    out_dir = tmp_path / "out"
    scenario.run(input_dir=in_dir, output_dir=out_dir)

    md = (out_dir / "meeting_summary_m000.md").read_text(encoding="utf-8")
    assert "| 담당자 | 할 일 | 기한 |" in md
    assert "| 김사장 | A | 2026-05-10 |" in md
    assert "| 이대리 | B | 2026-05-12 |" in md
    assert "| 박과장 | C | 2026-05-14 |" in md


# ---------------------------------------------------------------------------
# 8. 빈 액션 아이템 → placeholder
# ---------------------------------------------------------------------------


def test_run_empty_action_items_shows_placeholder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    response = MeetingSummary(
        summary="요약만 있고 액션 없음",
        action_items=[],
        decisions=[],
    )
    in_dir = _seed_input(tmp_path, n=1)
    _mock_summarize(monkeypatch, response=response)
    out_dir = tmp_path / "out"
    scenario.run(input_dir=in_dir, output_dir=out_dir)

    md = (out_dir / "meeting_summary_m000.md").read_text(encoding="utf-8")
    assert "추출된 액션 아이템 없음" in md
    assert "추출된 결정사항 없음" in md


# ---------------------------------------------------------------------------
# 9. summary["files"] metadata
# ---------------------------------------------------------------------------


def test_run_summary_files_metadata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    in_dir = _seed_input(tmp_path, n=2)
    _mock_summarize(monkeypatch)
    out_dir = tmp_path / "out"
    result = scenario.run(input_dir=in_dir, output_dir=out_dir)

    files = result["extras"]["files"]
    assert isinstance(files, list)
    assert len(files) == 2
    for entry in files:
        assert "input" in entry
        assert "output" in entry
        assert "n_actions" in entry
        assert "n_decisions" in entry
        assert isinstance(entry["n_actions"], int)
        assert isinstance(entry["n_decisions"], int)


# ---------------------------------------------------------------------------
# 10. underscore prefix 파일 skip
# ---------------------------------------------------------------------------


def test_run_skips_underscore_prefix_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    in_dir = _seed_input(
        tmp_path,
        n=2,
        extra_files={"_temp.txt": "ignore me", "_notes.txt": "skip"},
    )
    _mock_summarize(monkeypatch)
    out_dir = tmp_path / "out"
    result = scenario.run(input_dir=in_dir, output_dir=out_dir)

    # _meeting_meta.json + _temp.txt + _notes.txt 모두 skip
    assert result["metrics"]["processed"] == 2
    assert result["metrics"]["errors"] == 0


# ---------------------------------------------------------------------------
# 11. 빈 디렉토리
# ---------------------------------------------------------------------------


def test_run_zero_transcripts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    # personas fallback도 빈 디렉토리
    empty_seed = tmp_path / "empty_seed"
    empty_seed.mkdir()
    monkeypatch.setattr(scenario, "_DEFAULT_IN", empty_seed)

    _mock_summarize(monkeypatch)
    out_dir = tmp_path / "out"
    result = scenario.run(input_dir=in_dir, output_dir=out_dir)

    assert result["metrics"]["processed"] == 0
    assert result["metrics"]["errors"] == 0
    assert result["extras"]["files"] == []


# ---------------------------------------------------------------------------
# 12. output 디렉토리 자동 생성
# ---------------------------------------------------------------------------


def test_run_creates_output_dir_if_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    in_dir = _seed_input(tmp_path, n=1)
    _mock_summarize(monkeypatch)
    out_dir = tmp_path / "deep" / "nested" / "out"
    assert not out_dir.exists()

    scenario.run(input_dir=in_dir, output_dir=out_dir)
    assert out_dir.exists()
    assert (out_dir / "meeting_summary_m000.md").exists()


# ---------------------------------------------------------------------------
# 13. attendees 인자 전달 검증
# ---------------------------------------------------------------------------


def test_run_passes_attendees_to_summarize_meeting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """파일별 attendees가 다를 때 summarize_meeting 호출 인자도 그에 맞아야 함."""
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    (in_dir / "m000.txt").write_text("본문 A", encoding="utf-8")
    (in_dir / "m001.txt").write_text("본문 B", encoding="utf-8")
    meta = [
        {"filename": "m000.txt", "attendees": ["김사장", "이대리"]},
        {"filename": "m001.txt", "attendees": ["김사장", "박과장", "최주임"]},
    ]
    (in_dir / scenario.DEFAULT_META_FILENAME).write_text(json.dumps(meta), encoding="utf-8")

    calls: list[dict[str, object]] = []
    _mock_summarize(monkeypatch, capture_calls=calls)

    out_dir = tmp_path / "out"
    scenario.run(input_dir=in_dir, output_dir=out_dir)

    assert len(calls) == 2
    by_transcript = {c["transcript"]: c["attendees"] for c in calls}
    assert by_transcript["본문 A"] == ["김사장", "이대리"]
    assert by_transcript["본문 B"] == ["김사장", "박과장", "최주임"]


# ---------------------------------------------------------------------------
# 14. _format_markdown — 오늘 날짜 포함
# ---------------------------------------------------------------------------


def test_format_markdown_includes_today_date() -> None:
    md = scenario._format_markdown(
        "m000",
        "transcript preview",
        MeetingSummary(summary="요약", action_items=[], decisions=[]),
    )
    today = date.today().isoformat()
    assert today in md
    # ISO 형식 (YYYY-MM-DD) 패턴 검증 — 날짜가 실제 형식인지
    assert re.search(r"\d{4}-\d{2}-\d{2}", md)


# ---------------------------------------------------------------------------
# 15. _format_markdown — transcript preview 200자 truncate
# ---------------------------------------------------------------------------


def test_format_markdown_truncates_transcript_preview() -> None:
    long_text = "가" * 500
    md = scenario._format_markdown(
        "m000",
        long_text,
        MeetingSummary(summary="요약", action_items=[], decisions=[]),
    )
    # markdown 안에서 가장 긴 "가...가" 시퀀스를 추출해 길이 검증
    matches = re.findall(r"가+", md)
    longest = max(matches, key=len)
    assert len(longest) <= 200
