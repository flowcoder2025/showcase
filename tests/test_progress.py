"""T40 — ProgressEvent + helpers + rich_progress_adapter contract tests.

Coverage:
- ProgressEvent TypedDict 필드 형식
- ``step`` / ``done`` builder 동작
- ``emit`` fire-and-forget (None / 정상 / 예외 swallow)
- ``rich_progress_adapter`` context manager — start/stop, multi-step 갱신,
  단발 case (step 발행 0건) leak 없음
"""

from __future__ import annotations

from typing import Any

import pytest
from flowcoder_office_tools.progress import (
    ProgressEvent,
    done,
    emit,
    rich_progress_adapter,
    step,
)


def test_progress_event_typeddict_shape() -> None:
    evt: ProgressEvent = {
        "kind": "step",
        "case_id": "case07",
        "message": "img_001.png",
        "index": 1,
        "total": 100,
        "extra": {},
    }
    assert evt["case_id"] == "case07"
    assert evt["index"] == 1
    assert evt["total"] == 100


def test_step_builder_sets_kind_and_extras() -> None:
    evt = step("case07", "img_001.png", 5, 100, elapsed_ms=320)
    assert evt["kind"] == "step"
    assert evt["case_id"] == "case07"
    assert evt["message"] == "img_001.png"
    assert evt["index"] == 5
    assert evt["total"] == 100
    assert evt["extra"] == {"elapsed_ms": 320}


def test_done_builder_omits_index_total() -> None:
    evt = done("case07", "완료", processed=42)
    assert evt["kind"] == "done"
    assert evt["index"] is None
    assert evt["total"] is None
    assert evt["extra"] == {"processed": 42}


def test_emit_with_none_callback_is_noop() -> None:
    """``cb=None`` 일 때 예외 없이 silently skip."""
    emit(None, step("case07", "x", 1, 10))


def test_emit_dispatches_to_callback() -> None:
    received: list[ProgressEvent] = []
    emit(received.append, step("case07", "x", 1, 10))
    assert len(received) == 1
    assert received[0]["index"] == 1


def test_emit_swallows_callback_exceptions() -> None:
    """callback 예외가 scenario 본 흐름을 끊으면 안 된다 (R2-H3)."""

    def raising_cb(evt: ProgressEvent) -> None:
        raise RuntimeError("simulated callback failure")

    # Must not raise
    emit(raising_cb, step("case07", "x", 1, 10))


def test_rich_progress_adapter_handles_steps() -> None:
    """multi-step 이벤트 스트림 — task 추가 + 진행 갱신, 종료 시 cleanup."""
    with rich_progress_adapter("case07: OCR") as cb:
        cb(step("case07", "img_001.png", 1, 10))
        cb(step("case07", "img_005.png", 5, 10))
        cb(step("case07", "img_010.png", 10, 10))
    # 컨텍스트 종료 후 progress 객체가 정리됐는지는 외부에서 직접 검증 못 하지만
    # 예외 없이 완주하면 OK. 다음 with 블록도 독립적으로 동작 가능해야.
    with rich_progress_adapter("case08: OCR") as cb2:
        cb2(step("case08", "inv_001.png", 1, 5))


def test_rich_progress_adapter_no_step_no_leak() -> None:
    """단발 case (step 발행 0건) — context exit 시 자원 정리, 후속 호출 OK."""
    with rich_progress_adapter("case01: 단발") as cb:
        # 진행 발행 없이 종료
        _ = cb
    # 두 번 연속 사용해도 leak 없음
    with rich_progress_adapter("case02: 단발 2") as cb2:
        _ = cb2


def test_rich_progress_adapter_ignores_done_event() -> None:
    """``kind="done"`` 이벤트는 진행바 갱신을 건너뛴다."""
    with rich_progress_adapter("case07: OCR") as cb:
        cb(step("case07", "img_001.png", 1, 1))
        cb(done("case07", "완료"))


def test_rich_progress_adapter_ignores_event_without_total() -> None:
    """``index/total=None`` 이벤트는 무시 (start/warn 등)."""
    with rich_progress_adapter("case07: OCR") as cb:
        warn_event: ProgressEvent = {
            "kind": "warn",
            "case_id": "case07",
            "message": "rate-limited",
            "index": None,
            "total": None,
            "extra": {},
        }
        cb(warn_event)


# --- Scenario-level integration: progress_cb 를 받아서 step 발행 ------------


def test_case07_emits_progress_per_image(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """case07 scenario 가 OCR 루프마다 progress_cb 발행."""
    from flowcoder_office_tools.ocr import receipt
    from flowcoder_office_tools.ocr.receipt import ReceiptData
    from PIL import Image

    from cases.case07_ocr_receipt_to_excel import scenario

    monkeypatch.setattr(
        receipt,
        "extract",
        lambda _p: ReceiptData(
            merchant="스타벅스",
            amount=5500,
            date="2026-04-15",
            items=[],
            raw_text="스타벅스 5500",
        ),
    )

    in_dir = tmp_path / "in"
    in_dir.mkdir()
    for i in range(3):
        Image.new("RGB", (10, 10), "white").save(in_dir / f"r{i:03d}.png")

    received: list[ProgressEvent] = []
    scenario.run(
        input_dir=in_dir,
        output_dir=tmp_path / "out",
        progress_cb=received.append,
    )
    # 3 step + 1 done = 4 이벤트
    step_events = [e for e in received if e["kind"] == "step"]
    done_events = [e for e in received if e["kind"] == "done"]
    assert len(step_events) == 3, f"expected 3 step events, got {len(step_events)}"
    assert len(done_events) == 1
    assert step_events[-1]["index"] == 3
    assert step_events[-1]["total"] == 3


def test_case04_emits_progress_per_row(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """case04 scenario 가 Discord 알림 루프마다 progress_cb 발행."""
    import pandas as pd
    from flowcoder_office_tools.messaging import discord

    from cases.case04_discord_overdue_alert import scenario

    monkeypatch.setattr(discord, "send_with_level", lambda **_: {"status": 204})

    in_dir = tmp_path / "in"
    in_dir.mkdir()
    df = pd.DataFrame(
        [
            {
                "거래처명": "A",
                "거래번호": "INV-1",
                "금액": 1_000_000,
                "납기일": "2026-04-01",
                "연체일": 7,
            },
            {
                "거래처명": "B",
                "거래번호": "INV-2",
                "금액": 500_000,
                "납기일": "2026-04-05",
                "연체일": 14,
            },
        ]
    )
    df.to_excel(in_dir / "overdue_invoices.xlsx", index=False)

    received: list[ProgressEvent] = []
    scenario.run(
        input_dir=in_dir,
        output_dir=tmp_path / "out",
        progress_cb=received.append,
    )
    step_events = [e for e in received if e["kind"] == "step"]
    assert len(step_events) == 2
