"""before/after 시간 측정 — 시연 임팩트용."""

import time
from collections.abc import Iterator
from contextlib import contextmanager

from core.common.demo_logger import Logger

# Cap for ratio (above this is not credible on a projector).
# Floor is defensive depth — _RATIO_CAP is the binding guard for all realistic
# `before_minutes` values. See Task 4.5 review.
_RATIO_CAP = 10000
_ELAPSED_FLOOR_S = 0.05


@contextmanager
def measure(
    log: Logger,
    label: str,
    *,
    before_minutes: float | None = None,
) -> Iterator[None]:
    """경과시간을 콘솔에 출력. before_minutes가 주어지면 배수 계산.

    Ratio is clamped to avoid demo-time absurdity for sub-second operations.
    """
    start = time.perf_counter()
    log.info(f"⏱ {label} 시작")
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        if before_minutes is not None:
            elapsed_safe = max(elapsed, _ELAPSED_FLOOR_S)
            ratio = min((before_minutes * 60) / elapsed_safe, _RATIO_CAP)
            log.success(
                f"⏱ {label} 완료: before {before_minutes}m → after {elapsed:.2f}s (~{ratio:.0f}배)"
            )
        else:
            log.success(f"⏱ {label} 완료: {elapsed:.2f}s")
