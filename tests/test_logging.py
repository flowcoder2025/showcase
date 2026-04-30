from core.common import logging as demo_logging


def test_demo_logger_returns_object_with_methods():
    log = demo_logging.demo_logger("test_case")
    assert callable(getattr(log, "info", None))
    assert callable(getattr(log, "success", None))
    assert callable(getattr(log, "warning", None))


def test_logger_masks_secrets_in_messages(capsys):
    log = demo_logging.demo_logger("test_case")
    log.info("posting to https://discord.com/api/webhooks/x/secrettoken")
    captured = capsys.readouterr()
    assert "secrettoken" not in captured.out
    assert "***" in captured.out
