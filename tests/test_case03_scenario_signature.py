"""T38 — case03 scenario signature smoke test."""

from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from cases._protocols import ScenarioResult
from cases.case03_email_quote_dispatch import scenario


def test_case03_returns_scenario_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GMAIL_SENDER", "x@example.com")
    from core.docgen import pdf as pdf_mod
    from core.messaging import email as email_mod

    monkeypatch.setattr(
        pdf_mod, "md_to_pdf", lambda md, out, **_: Path(out).write_bytes(b"%PDF-1.4 stub")
    )
    monkeypatch.setattr(
        email_mod,
        "send",
        lambda msg, **_: {
            "transport": "safe-fallback",
            "sent": False,
            "to": str(msg["To"] or ""),
            "message_id": None,
            "note": "stub",
        },
    )

    in_dir = tmp_path / "in"
    in_dir.mkdir()
    df = pd.DataFrame(
        [
            {
                "거래처명": "A",
                "담당자": "담당",
                "이메일": "to@example.com",
                "견적번호": "Q-001",
                "품목요약": "x",
                "예상금액": 1000,
                "과거거래": "신규",
            }
        ]
    )
    df.to_excel(in_dir / "quote_dispatch_list.xlsx", index=False)

    result: ScenarioResult = scenario.run(input_dir=in_dir, output_dir=tmp_path / "out")
    assert result["case_id"] == "case03"
    assert "built" in result["metrics"]
    _: dict[str, Any] = result["extras"]["transports"]
    _msg_check: list[EmailMessage] = []  # not used, just typing import sanity
