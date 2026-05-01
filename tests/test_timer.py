import time

from core.common import demo_logger, timer


def test_measure_prints_before_after_with_ratio(capsys):
    log = demo_logger.demo_logger("t")
    with timer.measure(log, "op", before_minutes=180):
        time.sleep(0.01)
    captured = capsys.readouterr()
    assert "180m" in captured.out or "180분" in captured.out
    assert "배" in captured.out or "x" in captured.out


def test_measure_ratio_clamped_for_subsecond_ops(capsys):
    """Regression: 1ms op with 180min before should NOT print 1M+ ratio."""
    log = demo_logger.demo_logger("t")
    with timer.measure(log, "fast", before_minutes=180):
        pass  # near-instant
    captured = capsys.readouterr()
    import re

    m = re.search(r"~(\d+)배", captured.out)
    assert m is not None, f"ratio not found in: {captured.out!r}"
    assert int(m.group(1)) <= 10000, f"ratio {m.group(1)} exceeds 10000 cap"
