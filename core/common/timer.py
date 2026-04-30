"""before/after 시간 측정 — 시연 임팩트용."""
import time
from contextlib import contextmanager


@contextmanager
def measure(log, label: str, *, before_minutes: float | None = None):
    """경과시간을 콘솔에 출력. before_minutes가 주어지면 배수 계산."""
    start = time.perf_counter()
    log.info(f"⏱ {label} 시작")
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        if before_minutes is not None:
            ratio = (before_minutes * 60) / max(elapsed, 1e-6)
            log.success(
                f"⏱ {label} 완료: before {before_minutes}m → after {elapsed:.2f}s (~{ratio:.0f}배)"
            )
        else:
            log.success(f"⏱ {label} 완료: {elapsed:.2f}s")
