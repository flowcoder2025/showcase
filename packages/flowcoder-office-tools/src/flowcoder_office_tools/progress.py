"""Progress event contract — fire-and-forget signature for scenario callbacks (T35/T38/T40, R2-H3).

`progress_cb: Callable[[ProgressEvent], None]` — scenario가 진행 상황을 보고할
때 호출. CLI는 ``rich_progress_adapter`` 로 진행바 표시, Streamlit은 진행바
갱신, future webapp은 SSE 등으로 재발신. 예외는 ``emit`` 헬퍼가 swallow
(fire-and-forget) — scenario 본 흐름을 끊지 않는다.

T40 (R2-H3 / R2-H4): 5 case (case03/04/07/08/10) 가 루프 안에서 ``emit`` 으로
``step`` 이벤트 발행. ``runner.py`` 는 메뉴 실행 시 ``rich_progress_adapter`` 를
default progress_cb 로 wire — 사용자가 외부에서 호출 시 직접 progress_cb 전달.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any, TypedDict


class ProgressEvent(TypedDict):
    """Scenario 진행 단계 보고.

    Fields:
        kind: 이벤트 종류 — ``start`` / ``step`` / ``done`` / ``warn`` / ``error``.
        case_id: 발신 case 식별자 (예: ``case01``).
        message: human-readable 단계 설명 (한글).
        index: 현재 단계 진행 수 (multi-step에서만).
        total: 전체 단계 수 (multi-step에서만).
        extra: 자유 형식 추가 컨텍스트 (rate-limited backend 응답 등).
    """

    kind: str
    case_id: str
    message: str
    index: int | None
    total: int | None
    extra: dict[str, Any]


def step(
    case_id: str,
    message: str,
    index: int,
    total: int,
    **extra: Any,
) -> ProgressEvent:
    """``kind="step"`` 이벤트 빌더 — 루프 안에서 매 반복 발행."""
    return ProgressEvent(
        kind="step",
        case_id=case_id,
        message=message,
        index=index,
        total=total,
        extra=dict(extra),
    )


def done(case_id: str, message: str, **extra: Any) -> ProgressEvent:
    """``kind="done"`` 이벤트 빌더 — 시나리오 종료 시 1회 발행."""
    return ProgressEvent(
        kind="done",
        case_id=case_id,
        message=message,
        index=None,
        total=None,
        extra=dict(extra),
    )


def emit(cb: Callable[[ProgressEvent], None] | None, event: ProgressEvent) -> None:
    """Fire-and-forget — ``cb`` 가 None 이거나 예외 던지면 silently swallow.

    R2-H3: scenario 본 흐름이 callback 예외로 끊기지 않도록 하는 단일 진입점.
    호출 측은 항상 ``emit(progress_cb, step(...))`` 패턴 사용.
    """
    if cb is None:
        return
    try:
        cb(event)
    except Exception:  # noqa: BLE001 — fire-and-forget 계약 (R2-H3)
        pass


@contextmanager
def rich_progress_adapter(description: str) -> Iterator[Callable[[ProgressEvent], None]]:
    """``ProgressEvent`` 스트림 → ``rich.progress`` 진행바 어댑터 (context manager).

    첫 ``step`` 이벤트에서 task 추가, 이후 ``index`` 증가 시 갱신. ``index/total`` 이
    None 인 이벤트(start, warn 등)는 무시. ``with`` 블록 종료 시 진행바 자원이
    finally 로 항상 정리됨 — step 발행이 없는 단발 case 도 leak 없음.

    runner.py CLI 가 메뉴 실행 시 default progress_cb 로 wire. Streamlit/SSE
    어댑터는 별도(T47).

    Usage::

        with rich_progress_adapter("case07: 영수증 OCR") as cb:
            scenario.run(progress_cb=cb, ...)
    """
    from rich.progress import (
        BarColumn,
        Progress,
        TaskID,
        TextColumn,
        TimeRemainingColumn,
    )

    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
    )
    progress.start()
    task_id_holder: dict[str, TaskID] = {}

    def cb(evt: ProgressEvent) -> None:
        index = evt["index"]
        total = evt["total"]
        if evt["kind"] == "done" or total is None or index is None:
            return

        if "task_id" not in task_id_holder:
            task_id_holder["task_id"] = progress.add_task(description, total=total)

        progress.update(
            task_id_holder["task_id"],
            completed=index,
            description=f"{description}: {evt.get('message', '')}",
        )

    try:
        yield cb
    finally:
        progress.stop()
