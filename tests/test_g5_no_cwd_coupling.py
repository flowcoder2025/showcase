"""T39 (G5) — 모든 case가 임의 cwd에서 호출 가능한지 전수 검증.

T38 이 절대 경로 default 를 적용해 G5 cwd-coupling 은 거의 차단되어 있어야
한다. 본 테스트는 그 가정을 10 case 전수로 회귀-방어한다.

각 테스트는:
- ``monkeypatch.chdir(foreign)`` 으로 cwd 를 임의 디렉터리로 이동
- input 데이터는 절대 경로(``tmp_path``) 로 합성
- ``scenario.run(input_dir=..., output_dir=..., ...)`` 호출
- ``ScenarioResult`` 가 정상 반환되는지 확인

회귀가 발생하면(예: scenario 안에서 ``Path("personas/...")`` 같은 cwd-coupled
참조가 추가되면) 본 테스트가 ``FileNotFoundError`` 로 즉시 실패한다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from PIL import Image

from cases._protocols import ScenarioResult


@pytest.fixture
def foreign_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """임의 cwd 로 이동 — scenario 가 이 cwd 에 의존하면 안 된다."""
    foreign = tmp_path / "foreign_cwd"
    foreign.mkdir()
    monkeypatch.chdir(foreign)
    return foreign


def test_case01_runs_from_arbitrary_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, foreign_cwd: Path
) -> None:
    from cases.case01_excel_vendor_report import scenario

    in_dir = tmp_path / "in"
    in_dir.mkdir()
    df = pd.DataFrame(
        [
            {"거래처명": "A", "거래일": "2026-01-15", "금액": 100},
            {"거래처명": "B", "거래일": "2026-02-10", "금액": 200},
        ]
    )
    df.to_excel(in_dir / "data.xlsx", index=False)

    result: ScenarioResult = scenario.run(input_dir=in_dir, output_dir=tmp_path / "out")
    assert result["case_id"] == "case01"
    assert all(p.exists() for p in result["output_files"])


def test_case02_runs_from_arbitrary_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, foreign_cwd: Path
) -> None:
    from cases.case02_excel_invoice_validation import scenario
    from core.messaging import discord

    monkeypatch.setattr(discord, "send", lambda *a, **k: {"status": 204})

    in_dir = tmp_path / "in"
    in_dir.mkdir()
    df = pd.DataFrame(
        [
            {
                "거래처명": "A",
                "거래명세서번호": "INV-1",
                "품목": "X",
                "단가": 1000,
                "수량": 10,
                "금액": 10_000,
            },
        ]
    )
    df.to_excel(in_dir / "invoices.xlsx", index=False)

    result: ScenarioResult = scenario.run(
        input_dir=in_dir,
        output_dir=tmp_path / "out",
        config={"discord_alert": False},
    )
    assert result["case_id"] == "case02"


def test_case03_runs_from_arbitrary_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, foreign_cwd: Path
) -> None:
    monkeypatch.setenv("GMAIL_SENDER", "x@example.com")
    from cases.case03_email_quote_dispatch import scenario
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


def test_case04_runs_from_arbitrary_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, foreign_cwd: Path
) -> None:
    from cases.case04_discord_overdue_alert import scenario
    from core.messaging import discord

    monkeypatch.setattr(discord, "send_with_level", lambda **_: {"status": 204})

    in_dir = tmp_path / "in"
    in_dir.mkdir()
    df = pd.DataFrame(
        [
            {
                "거래처명": "A",
                "거래번호": "INV-1",
                "금액": 1_000_000,
                "납기일": "2026-04-01",
                "연체일": 7,
            }
        ]
    )
    df.to_excel(in_dir / "overdue_invoices.xlsx", index=False)

    result: ScenarioResult = scenario.run(input_dir=in_dir, output_dir=tmp_path / "out")
    assert result["case_id"] == "case04"


def test_case05_runs_from_arbitrary_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, foreign_cwd: Path
) -> None:
    from cases.case05_doc_quote_generator import scenario
    from core.docgen import pdf as pdf_mod

    monkeypatch.setattr(
        pdf_mod, "md_to_pdf", lambda md, out, **_: Path(out).write_bytes(b"%PDF-1.4 stub")
    )

    in_dir = tmp_path / "in"
    in_dir.mkdir()
    df = pd.DataFrame(
        [
            {
                "견적번호": "Q-001",
                "거래처명": "A",
                "담당자": "x",
                "이메일": "x@example.com",
                "품목": "p1",
                "수량": 1,
                "단가": 1000,
                "납기일": "2026-06-30",
            }
        ]
    )
    df.to_excel(in_dir / "quote_requests.xlsx", index=False)

    result: ScenarioResult = scenario.run(input_dir=in_dir, output_dir=tmp_path / "out")
    assert result["case_id"] == "case05"


_HWPX_TEMPLATE = (
    Path(__file__).resolve().parent.parent
    / "personas"
    / "sample_data"
    / "forms"
    / "grant_application_template.hwpx"
)


def test_case06_runs_from_arbitrary_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, foreign_cwd: Path
) -> None:
    from cases.case06_hwpx_govt_form_filler import scenario

    if not _HWPX_TEMPLATE.exists():
        pytest.skip("HWPX template fixture missing")

    result: ScenarioResult = scenario.run(
        output_dir=tmp_path / "out",
        config={"template_path": _HWPX_TEMPLATE},
    )
    assert result["case_id"] == "case06"


def test_case07_runs_from_arbitrary_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, foreign_cwd: Path
) -> None:
    from cases.case07_ocr_receipt_to_excel import scenario
    from core.ocr import receipt
    from core.ocr.receipt import ReceiptData

    monkeypatch.setattr(
        receipt,
        "extract",
        lambda _p: ReceiptData(
            merchant="스타벅스",
            amount=5500,
            date="2026-04-15",
            items=[],
            raw_text="스타벅스 5500",
        ),
    )

    in_dir = tmp_path / "in"
    in_dir.mkdir()
    Image.new("RGB", (10, 10), "white").save(in_dir / "r001.png")

    result: ScenarioResult = scenario.run(input_dir=in_dir, output_dir=tmp_path / "out")
    assert result["case_id"] == "case07"


def test_case08_runs_from_arbitrary_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, foreign_cwd: Path
) -> None:
    from cases.case08_ocr_invoice_to_csv import scenario
    from core.ocr import invoice
    from core.ocr.invoice import InvoiceData

    monkeypatch.setattr(
        invoice,
        "extract",
        lambda _p: InvoiceData(
            invoice_no="INV-001",
            issue_date="2026-04-01",
            supplier_biznum="220-81-62517",
            supplier_name="공급자",
            buyer_biznum="120-81-47521",
            buyer_name="공급받는자",
            line_items=[],
            total_supply=1_000_000,
            total_vat=100_000,
            total_amount=1_100_000,
        ),
    )

    in_dir = tmp_path / "in"
    in_dir.mkdir()
    Image.new("RGB", (10, 10), "white").save(in_dir / "inv_001.png")

    result: ScenarioResult = scenario.run(input_dir=in_dir, output_dir=tmp_path / "out")
    assert result["case_id"] == "case08"


def test_case09_runs_from_arbitrary_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, foreign_cwd: Path
) -> None:
    from cases.case09_ai_email_drafter import scenario
    from core.ai import client as ai_client

    fake_drafts = '[{"option": 1, "subject": "테스트", "body": "본문"}]'
    monkeypatch.setattr(ai_client, "chat", lambda messages, **k: fake_drafts)

    result: ScenarioResult = scenario.run(
        output_dir=tmp_path / "out",
        config={"incoming_message": "제목: t\n본문: b"},
    )
    assert result["case_id"] == "case09"


def test_case10_runs_from_arbitrary_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, foreign_cwd: Path
) -> None:
    from cases.case10_ai_meeting_summarizer import scenario
    from core.ai import tasks
    from core.ai.tasks import ActionItem, MeetingSummary

    monkeypatch.setattr(
        tasks,
        "summarize_meeting",
        lambda transcript, *, attendees, **k: MeetingSummary(
            summary="요약",
            action_items=[ActionItem(owner="김사장", task="x", due=None)],
            decisions=[],
        ),
    )

    in_dir = tmp_path / "in"
    in_dir.mkdir()
    (in_dir / "m000.txt").write_text("회의록", encoding="utf-8")
    meta = [{"filename": "m000.txt", "attendees": ["김사장"]}]
    (in_dir / scenario.DEFAULT_META_FILENAME).write_text(
        json.dumps(meta, ensure_ascii=False), encoding="utf-8"
    )

    result: ScenarioResult = scenario.run(input_dir=in_dir, output_dir=tmp_path / "out")
    assert result["case_id"] == "case10"


def test_safe_mode_cache_path_is_absolute() -> None:
    """T39 (G5) — ``safe_mode.cache_path`` 도 cwd 에 의존하지 않는다."""
    from core.common import safe_mode

    p = safe_mode.cache_path("case_x", "key")
    assert p.is_absolute(), f"cache_path returned relative path: {p}"


def test_safe_mode_cache_path_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``AX_CACHE_DIR`` env override 검증."""
    from core.common import safe_mode

    monkeypatch.setenv("AX_CACHE_DIR", str(tmp_path / "cases"))
    p = safe_mode.cache_path("case_x", "key")
    assert str(p).startswith(str(tmp_path / "cases"))
