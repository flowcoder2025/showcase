import time

from core.common import logging as demo_logging
from core.common import timer


def test_measure_prints_before_after_with_ratio(capsys):
    log = demo_logging.demo_logger("t")
    with timer.measure(log, "op", before_minutes=180):
        time.sleep(0.01)
    captured = capsys.readouterr()
    assert "180m" in captured.out or "180분" in captured.out
    assert "배" in captured.out or "x" in captured.out
