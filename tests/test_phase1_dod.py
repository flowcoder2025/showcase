"""Phase 1 DoD — spec §13의 측정 가능 기준을 자동 검증."""

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


def test_critical_imports_smoke() -> None:
    """uv sync 대신 핵심 모듈 import + public API 노출까지 검증.

    `assert all(m is not None ...)`은 import 성공 시 항상 True인 tautology이므로
    실제 public API가 노출됐는지(hasattr) 검증한다. import 자체가 실패하면
    pytest가 ImportError로 즉시 fail한다.
    """
    import importlib

    for mod in (
        "pandas",
        "openpyxl",
        "openai",
        "discord_webhook",
        "yaml",
        "rich",
        # Phase 2 신규 의존성 (T0). weasyprint는 system libs 의존성 때문에 T5에서 결정 보류.
        "lxml.etree",
    ):
        importlib.import_module(mod)
    from flowcoder_office_tools.ai import client, prompts, tasks
    from flowcoder_office_tools.common import config, demo_logger, safe_mode, secrets_mask, timer
    from flowcoder_office_tools.excel import merger, pivot, reader, validator, writer
    from flowcoder_office_tools.messaging import discord

    # core.ai
    assert hasattr(client, "chat")
    assert hasattr(client, "MODEL_PRIORITY")
    assert hasattr(client, "RateLimitError")
    assert hasattr(prompts, "EMAIL_DRAFT_SYSTEM")
    assert hasattr(tasks, "draft_email")

    # core.common
    assert hasattr(config, "load")
    assert hasattr(config, "repo_root")
    assert hasattr(demo_logger, "demo_logger")
    assert hasattr(timer, "measure")
    assert hasattr(secrets_mask, "mask_text")
    assert hasattr(safe_mode, "intercept")
    assert hasattr(safe_mode, "is_safe")
    assert hasattr(safe_mode, "force_safe")

    # core.excel
    assert hasattr(reader, "read_dir")
    assert hasattr(merger, "merge_by_vendor")
    assert hasattr(merger, "REQUIRED_KEYS")
    assert hasattr(pivot, "vendor_by_month")
    assert hasattr(writer, "write_styled_report")
    assert hasattr(validator, "detect_unit_price_outliers")

    # core.messaging
    assert hasattr(discord, "send")


def test_runner_check_exits_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/x/y")
    result = subprocess.run(
        [sys.executable, "runner.py", "--check"], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_case01_full_pipeline_creates_report(tmp_path: Path) -> None:
    """case01: column_map → merge → pivot → report."""
    import pandas as pd

    df = pd.DataFrame(
        [
            {"거래처명": "A", "거래일": "2026-01-01", "금액": 100},
            {"거래처명": "B", "거래일": "2026-02-01", "금액": 200},
        ]
    )
    inp = tmp_path / "input"
    inp.mkdir()
    df.to_excel(inp / "data.xlsx", index=False)

    from cases.case01_excel_vendor_report import scenario

    out_dir = tmp_path / "out"
    result = scenario.run(input_dir=inp, output_dir=out_dir)
    assert result["output_files"][0].exists()


def test_case09_safe_mode_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """동일 입력 2회 실행 → drafts.json 동일 (T38: config["incoming_message"])."""
    import json

    monkeypatch.setenv("DEMO_SAFE", "1")

    fake_drafts = '[{"option": 1, "subject": "fixed", "body": "fixed-body"}]'
    from flowcoder_office_tools.ai import client as ai_client

    monkeypatch.setattr(ai_client, "chat", lambda messages, **k: fake_drafts)

    from cases.case09_ai_email_drafter import scenario

    incoming = "제목: t\n본문: b"
    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"
    r1 = scenario.run(output_dir=out1, config={"incoming_message": incoming})
    r2 = scenario.run(output_dir=out2, config={"incoming_message": incoming})
    text1 = r1["output_files"][0].read_text()
    text2 = r2["output_files"][0].read_text()
    assert text1 == text2
    parsed = json.loads(text1)
    assert len(parsed) == 1
    assert parsed[0]["subject"] == "fixed"


def test_openrouter_fallback_chain(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """primary 차단 → fallback 자동 → 마지막 실패 시 force_safe."""
    from flowcoder_office_tools.ai import client

    def always_429(model: str, messages: list[dict[str, Any]], **k: Any) -> str:
        raise client.RateLimitError("429")

    monkeypatch.setattr(client, "_call", always_429)
    monkeypatch.setenv("DEMO_SAFE", "0")
    result = client.chat([{"role": "user", "content": "hi"}])
    out = capsys.readouterr().out
    assert "AUTO-SAFE" in out
    assert result == "[SAFE-FALLBACK]"


def test_secrets_masking_in_logs(capsys: pytest.CaptureFixture[str]) -> None:
    from flowcoder_office_tools.common.demo_logger import demo_logger

    log = demo_logger("dod")
    log.info("posting to https://discord.com/api/webhooks/123/secret")
    out = capsys.readouterr().out
    assert "secret" not in out
    assert "***" in out


def test_safe_mode_patch_isolation_across_cases(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEMO_SAFE", "1")
    from flowcoder_office_tools.common import safe_mode
    from flowcoder_office_tools.messaging import discord as d

    original = d.send
    with safe_mode.intercept("A", apis=["discord_webhook"]):
        assert d.send is not original
    assert d.send is original
    with safe_mode.intercept("B", apis=["discord_webhook"]):
        assert d.send is not original
    assert d.send is original


def test_column_map_reuse_with_different_schema(tmp_path: Path) -> None:
    """다음 컨설팅 프로젝트 시나리오 — 영어 컬럼."""
    import pandas as pd
    from flowcoder_office_tools.excel import merger

    df = pd.DataFrame(
        [
            {"Customer": "X", "TxDate": "2026-01-01", "Total": 100},
        ]
    )
    df.to_excel(tmp_path / "d.xlsx", index=False)
    result = merger.merge_by_vendor(
        tmp_path, column_map={"vendor": "Customer", "date": "TxDate", "amount": "Total"}
    )
    assert result["amount"].sum() == 100
