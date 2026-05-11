"""Tests for case04 — 미수금 단계별 Discord 알림 (T38 ScenarioResult)."""

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

_INPUT_NAME = "overdue_invoices.xlsx"


def _make_overdue_df(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def _write_input(in_dir: Path, df: pd.DataFrame) -> Path:
    in_dir.mkdir(parents=True, exist_ok=True)
    p = in_dir / _INPUT_NAME
    df.to_excel(p, index=False)
    return in_dir


@pytest.fixture
def overdue_input_dir(tmp_path: Path) -> Path:
    """4단계 분포가 보장된 60건 입력. (24/18/12/6 = friendly/neutral/strict/final)"""
    rows: list[dict[str, Any]] = []
    counts = [
        (24, 7, "friendly"),
        (18, 22, "neutral"),
        (12, 45, "strict"),
        (6, 90, "final"),
    ]
    seq = 0
    for n, days, _level in counts:
        for _ in range(n):
            seq += 1
            rows.append(
                {
                    "거래처명": f"AX_VENDOR_{seq:03d}",
                    "거래번호": f"INV-{seq:04d}",
                    "금액": 1_000_000,
                    "납기일": "2026-04-01",
                    "연체일": days,
                    "담당자": "박과장",
                }
            )
    return _write_input(tmp_path / "in", _make_overdue_df(rows))


def test_classify_level_boundaries() -> None:
    from cases.case04_discord_overdue_alert.scenario import classify_level

    assert classify_level(0) == "friendly"
    assert classify_level(14) == "friendly"
    assert classify_level(15) == "neutral"
    assert classify_level(30) == "neutral"
    assert classify_level(31) == "strict"
    assert classify_level(60) == "strict"
    assert classify_level(61) == "final"
    assert classify_level(9999) == "final"


def test_classify_level_negative_raises() -> None:
    from cases.case04_discord_overdue_alert.scenario import classify_level

    with pytest.raises(ValueError):
        classify_level(-1)


def test_run_dispatches_per_row_in_safe_mode(
    overdue_input_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from flowcoder_office_tools.messaging import discord

    from cases.case04_discord_overdue_alert import scenario

    sent: list[dict[str, Any]] = []

    def _capture(**kwargs: Any) -> dict[str, int]:
        sent.append(kwargs)
        return {"status": 204}

    monkeypatch.setattr(discord, "send_with_level", _capture)

    result = scenario.run(input_dir=overdue_input_dir, output_dir=tmp_path / "out")

    assert result["metrics"]["sent"] == 60
    assert len(sent) == 60


def test_run_summary_by_level_counts_correct(
    overdue_input_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from flowcoder_office_tools.messaging import discord

    from cases.case04_discord_overdue_alert import scenario

    monkeypatch.setattr(discord, "send_with_level", lambda **k: {"status": 204})

    result = scenario.run(input_dir=overdue_input_dir, output_dir=tmp_path / "out")
    by_level = result["extras"]["by_level"]

    assert set(by_level.keys()) == {"friendly", "neutral", "strict", "final"}
    assert by_level["friendly"] == 24
    assert by_level["neutral"] == 18
    assert by_level["strict"] == 12
    assert by_level["final"] == 6
    assert sum(by_level.values()) == 60


def test_run_uses_escape_for_vendor_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import rich.markup
    from flowcoder_office_tools.messaging import discord

    from cases.case04_discord_overdue_alert import scenario

    rows = [
        {
            "거래처명": "[브래킷] 회사",
            "거래번호": "INV-X",
            "금액": 500_000,
            "납기일": "2026-04-01",
            "연체일": 7,
            "담당자": "박과장",
        }
    ]
    in_dir = _write_input(tmp_path / "in", _make_overdue_df(rows))

    seen_titles: list[str] = []

    def _capture(**kwargs: Any) -> dict[str, int]:
        seen_titles.append(str(kwargs.get("title", "")))
        return {"status": 204}

    monkeypatch.setattr(discord, "send_with_level", _capture)

    scenario.run(input_dir=in_dir, output_dir=tmp_path / "out")

    expected_escaped = rich.markup.escape("[브래킷] 회사")
    assert any(expected_escaped in t for t in seen_titles), (
        f"escape 미적용 — titles: {seen_titles!r}"
    )
    assert all("[브래킷] 회사" not in t or expected_escaped in t for t in seen_titles)


def test_run_handles_zero_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from flowcoder_office_tools.messaging import discord

    from cases.case04_discord_overdue_alert import scenario

    df = pd.DataFrame(columns=["거래처명", "거래번호", "금액", "납기일", "연체일", "담당자"])
    in_dir = _write_input(tmp_path / "in", df)

    calls: list[Any] = []

    def _record(**kwargs: Any) -> dict[str, int]:
        calls.append(kwargs)
        return {"status": 204}

    monkeypatch.setattr(discord, "send_with_level", _record)

    result = scenario.run(input_dir=in_dir, output_dir=tmp_path / "out")

    assert result["metrics"]["sent"] == 0
    assert result["metrics"]["errors"] == 0
    assert len(calls) == 0


def test_run_continues_after_per_row_failure(
    overdue_input_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from flowcoder_office_tools.messaging import discord

    from cases.case04_discord_overdue_alert import scenario

    counter = {"n": 0}

    def _flaky(**kwargs: Any) -> dict[str, int]:
        counter["n"] += 1
        if counter["n"] == 1:
            raise RuntimeError("transient")
        return {"status": 204}

    monkeypatch.setattr(discord, "send_with_level", _flaky)

    result = scenario.run(input_dir=overdue_input_dir, output_dir=tmp_path / "out")

    assert result["metrics"]["errors"] >= 1
    assert result["metrics"]["sent"] >= 59
    assert result["metrics"]["sent"] + result["metrics"]["errors"] == 60


def test_case04_column_map_partial_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R2-C1 regression: ``config["column_map"]`` 부분 override 시 default 키 보존."""
    from flowcoder_office_tools.messaging import discord

    from cases.case04_discord_overdue_alert import scenario

    rows = [
        {
            "회사명": "AX_VENDOR_001",
            "거래번호": "INV-0001",
            "금액": 1_000_000,
            "납기일": "2026-04-01",
            "연체일": 7,
            "담당자": "박과장",
        }
    ]
    in_dir = _write_input(tmp_path / "in", _make_overdue_df(rows))

    sent: list[dict[str, Any]] = []

    def _capture(**kwargs: Any) -> dict[str, int]:
        sent.append(kwargs)
        return {"status": 204}

    monkeypatch.setattr(discord, "send_with_level", _capture)

    result = scenario.run(
        input_dir=in_dir,
        output_dir=tmp_path / "out",
        config={"column_map": {"vendor": "회사명"}},
    )

    assert result["metrics"]["sent"] == 1, f"부분 override 실패 — result={result!r}"
    assert result["metrics"]["errors"] == 0
    assert len(sent) == 1
    assert "AX_VENDOR_001" in sent[0]["title"]
