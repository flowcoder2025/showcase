from core.common import demo_logger


def test_demo_logger_returns_object_with_methods():
    log = demo_logger.demo_logger("test_case")
    assert callable(getattr(log, "info", None))
    assert callable(getattr(log, "success", None))
    assert callable(getattr(log, "warning", None))


def test_logger_masks_secrets_in_messages(capsys):
    log = demo_logger.demo_logger("test_case")
    log.info("posting to https://discord.com/api/webhooks/x/secrettoken")
    captured = capsys.readouterr()
    assert "secrettoken" not in captured.out
    assert "***" in captured.out


def test_logger_preserves_case_id_in_output(capsys):
    """Regression for rich-markup-eats-brackets bug."""
    log = demo_logger.demo_logger("case01")
    log.info("hello world")
    captured = capsys.readouterr()
    assert "case01" in captured.out


def test_warning_and_error_emit_to_console(capsys):
    log = demo_logger.demo_logger("c1")
    log.warning("warn message")
    log.error("err message")
    out = capsys.readouterr().out
    assert "WARN" in out
    assert "ERR" in out
    assert "c1" in out  # case_id preservation regression
    assert "warn message" in out
    assert "err message" in out


def test_logger_protocol_exists_and_is_public():
    """Logger Protocol is exposed as part of demo_logger module's public API."""
    from core.common.demo_logger import Logger

    # Sanity: DemoLogger structurally satisfies the Protocol
    log = demo_logger.demo_logger("c")
    assert isinstance(log, demo_logger.DemoLogger)
    # All 4 methods on Logger contract
    assert hasattr(Logger, "info")
    assert hasattr(Logger, "success")
    assert hasattr(Logger, "warning")
    assert hasattr(Logger, "error")
