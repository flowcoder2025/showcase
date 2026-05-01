"""Tests for case04 — 미수금 단계별 Discord 알림."""

from pathlib import Path
from typing import Any

import pandas as pd
import pytest


def _make_overdue_df(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """헬퍼: 미수금 입력 DataFrame을 생성한다."""
    return pd.DataFrame(rows)


@pytest.fixture
def overdue_input(tmp_path: Path) -> Path:
    """4단계 분포가 보장된 60건 입력. (24/18/12/6 = friendly/neutral/strict/final)"""
    rows: list[dict[str, Any]] = []
    counts = [
        (24, 7, "friendly"),  # 0~14일
        (18, 22, "neutral"),  # 15~30일
        (12, 45, "strict"),  # 31~60일
        (6, 90, "final"),  # 60+일
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
    df = _make_overdue_df(rows)
    p = tmp_path / "overdue.xlsx"
    df.to_excel(p, index=False)
    return p


def test_classify_level_boundaries() -> None:
    """경계값: 0/14/15/30/31/60/61/9999 + 음수 raise."""
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
    overdue_input: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """60건 input → send_with_level 60회 호출."""
    from cases.case04_discord_overdue_alert import scenario
    from core.messaging import discord

    sent: list[dict[str, Any]] = []

    def _capture(**kwargs: Any) -> dict[str, int]:
        sent.append(kwargs)
        return {"status": 204}

    monkeypatch.setattr(discord, "send_with_level", _capture)

    summary = scenario.run(input_path=overdue_input)

    assert summary["sent"] == 60
    assert len(sent) == 60


def test_run_summary_by_level_counts_correct(
    overdue_input: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """입력 분포 (24/18/12/6) → summary['by_level'] 정확 매칭."""
    from cases.case04_discord_overdue_alert import scenario
    from core.messaging import discord

    monkeypatch.setattr(discord, "send_with_level", lambda **k: {"status": 204})

    summary = scenario.run(input_path=overdue_input)

    assert set(summary["by_level"].keys()) == {"friendly", "neutral", "strict", "final"}
    assert summary["by_level"]["friendly"] == 24
    assert summary["by_level"]["neutral"] == 18
    assert summary["by_level"]["strict"] == 12
    assert summary["by_level"]["final"] == 6
    assert sum(summary["by_level"].values()) == 60


def test_run_uses_escape_for_vendor_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """vendor명에 [브래킷] 포함 → title에 escape 적용된 형태로 들어감."""
    import rich.markup

    from cases.case04_discord_overdue_alert import scenario
    from core.messaging import discord

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
    df = _make_overdue_df(rows)
    p = tmp_path / "in.xlsx"
    df.to_excel(p, index=False)

    seen_titles: list[str] = []

    def _capture(**kwargs: Any) -> dict[str, int]:
        seen_titles.append(str(kwargs.get("title", "")))
        return {"status": 204}

    monkeypatch.setattr(discord, "send_with_level", _capture)

    scenario.run(input_path=p)

    expected_escaped = rich.markup.escape("[브래킷] 회사")
    assert any(expected_escaped in t for t in seen_titles), (
        f"escape 미적용 — titles: {seen_titles!r}"
    )
    # 추가: 원문 그대로(미escape)는 들어가지 않아야 함 — escape 결과와 다르다.
    assert all("[브래킷] 회사" not in t or expected_escaped in t for t in seen_titles)


def test_run_handles_zero_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """빈 DataFrame → sent==0, errors==0, 예외 없음."""
    from cases.case04_discord_overdue_alert import scenario
    from core.messaging import discord

    df = pd.DataFrame(columns=["거래처명", "거래번호", "금액", "납기일", "연체일", "담당자"])
    p = tmp_path / "empty.xlsx"
    df.to_excel(p, index=False)

    calls: list[Any] = []

    def _record(**kwargs: Any) -> dict[str, int]:
        calls.append(kwargs)
        return {"status": 204}

    monkeypatch.setattr(discord, "send_with_level", _record)

    summary = scenario.run(input_path=p)

    assert summary["sent"] == 0
    assert summary["errors"] == 0
    assert len(calls) == 0


def test_run_continues_after_per_row_failure(
    overdue_input: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """한 row가 raise해도 나머지 진행. errors >= 1, sent >= rest."""
    from cases.case04_discord_overdue_alert import scenario
    from core.messaging import discord

    counter = {"n": 0}

    def _flaky(**kwargs: Any) -> dict[str, int]:
        counter["n"] += 1
        # 첫 호출만 raise — 나머지는 정상
        if counter["n"] == 1:
            raise RuntimeError("transient")
        return {"status": 204}

    monkeypatch.setattr(discord, "send_with_level", _flaky)

    summary = scenario.run(input_path=overdue_input)

    assert summary["errors"] >= 1
    assert summary["sent"] >= 59  # 60 입력 - 1 실패
    assert summary["sent"] + summary["errors"] == 60
