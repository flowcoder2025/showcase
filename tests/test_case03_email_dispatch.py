"""Tests for case03 — 견적 메일 일괄 발송 (개인화 + PDF 첨부).

T38: scenario.run() 시그니처가 ``(*, input_dir, output_dir, config)`` 으로 정식화되어
각 테스트가 ``quote_dispatch_list.xlsx`` 를 ``input_dir`` 안에 생성하고 ScenarioResult
의 ``metrics`` / ``extras`` 를 통해 검증한다.
"""

from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

_INPUT_NAME = "quote_dispatch_list.xlsx"


class _CaptureLogger:
    """In-memory logger — assert per-request log lines."""

    def __init__(self) -> None:
        self.infos: list[str] = []
        self.successes: list[str] = []
        self.warnings: list[str] = []
        self.errors: list[str] = []

    def info(self, msg: str) -> None:
        self.infos.append(msg)

    def success(self, msg: str) -> None:
        self.successes.append(msg)

    def warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def error(self, msg: str) -> None:
        self.errors.append(msg)


def _stub_pdf_ok(md_path: Path | str, out_path: Path | str, **_kw: Any) -> None:
    """md_to_pdf mock — 빈 PDF stub 작성."""
    Path(out_path).write_bytes(b"%PDF-1.4\n%stub")


def _safe_send(msg: EmailMessage, **_kw: Any) -> dict[str, Any]:
    """email.send mock — safe-fallback 반환 (T7b 패턴)."""
    return {
        "transport": "safe-fallback",
        "sent": False,
        "to": str(msg["To"] or ""),
        "message_id": None,
        "note": "test stub",
    }


def _make_dispatch_df(n: int = 50) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for i in range(1, n + 1):
        rows.append(
            {
                "거래처명": f"거래처{i:02d}",
                "담당자": f"담당자{i:02d}",
                "이메일": f"v{i}@example.com",
                "견적번호": f"Q-2026-{i:03d}",
                "품목요약": f"품목{i}",
                "예상금액": 1_000_000 + i * 1_000,
                "과거거래": f"과거이력-{i}",
            }
        )
    return pd.DataFrame(rows)


def _write_input(in_dir: Path, df: pd.DataFrame) -> None:
    in_dir.mkdir(parents=True, exist_ok=True)
    df.to_excel(in_dir / _INPUT_NAME, index=False)


@pytest.fixture
def dispatch_input_dir(tmp_path: Path) -> Path:
    in_dir = tmp_path / "in"
    _write_input(in_dir, _make_dispatch_df(50))
    return in_dir


@pytest.fixture(autouse=True)
def _set_sender_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """case03 build_message 호출에 GMAIL_SENDER 필요 — 모든 테스트에 fixture 적용."""
    monkeypatch.setenv("GMAIL_SENDER", "ax-sales@example.com")


def _patch_externals(
    monkeypatch: pytest.MonkeyPatch,
    *,
    pdf_fn: Any = _stub_pdf_ok,
    send_fn: Any = _safe_send,
) -> list[EmailMessage]:
    """pdf.md_to_pdf + email.send를 mock; 실제 호출된 EmailMessage 캡처."""
    from core.docgen import pdf as pdf_mod
    from core.messaging import email as email_mod

    captured: list[EmailMessage] = []

    def capture_send(msg: EmailMessage, **kw: Any) -> dict[str, Any]:
        captured.append(msg)
        return send_fn(msg, **kw)  # type: ignore[no-any-return]

    monkeypatch.setattr(pdf_mod, "md_to_pdf", pdf_fn)
    monkeypatch.setattr(email_mod, "send", capture_send)
    return captured


# --- Tests -----------------------------------------------------------------


def test_run_safe_mode_builds_50_messages(
    dispatch_input_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """50건 입력 → built==50, sent==50 (safe-fallback도 카운트)."""
    from cases.case03_email_quote_dispatch import scenario

    captured = _patch_externals(monkeypatch)
    out = tmp_path / "out"

    result = scenario.run(input_dir=dispatch_input_dir, output_dir=out)

    assert result["metrics"]["built"] == 50
    assert result["metrics"]["sent"] == 50
    assert result["metrics"]["errors"] == 0
    assert len(captured) == 50


def test_run_per_request_logs_quote_no(
    dispatch_input_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """각 row마다 quote_no가 info 로그에 등장."""
    from cases.case03_email_quote_dispatch import scenario

    _patch_externals(monkeypatch)
    cap = _CaptureLogger()
    monkeypatch.setattr(scenario, "demo_logger", lambda _case: cap)

    out = tmp_path / "out"
    scenario.run(input_dir=dispatch_input_dir, output_dir=out)

    quote_lines = [m for m in cap.infos if "Q-2026-" in m]
    assert len(quote_lines) == 50, f"expected 50 progress lines, got {len(quote_lines)}"


def test_run_uses_build_html_body_for_xss_safety(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """vendor에 <script> 포함 → HTML body는 escape됨, raw <script> 미포함."""
    from cases.case03_email_quote_dispatch import scenario

    captured = _patch_externals(monkeypatch)

    df = pd.DataFrame(
        [
            {
                "거래처명": "<script>alert(1)</script>",
                "담당자": "공격자",
                "이메일": "x@example.com",
                "견적번호": "Q-XSS-001",
                "품목요약": "안전 부품",
                "예상금액": 10_000,
                "과거거래": "신규",
            }
        ]
    )
    in_dir = tmp_path / "in"
    _write_input(in_dir, df)

    out = tmp_path / "out"
    scenario.run(input_dir=in_dir, output_dir=out)

    assert len(captured) == 1
    msg = captured[0]
    html_parts = [p.get_content() for p in msg.walk() if p.get_content_type() == "text/html"]
    assert html_parts, "no HTML alternative attached"
    html_body = html_parts[0]
    assert "<script>alert(1)</script>" not in html_body
    assert "&lt;script&gt;" in html_body


def test_run_attaches_pdf_when_generated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """md_to_pdf 성공 → build_message attachments에 .pdf 포함."""
    from cases.case03_email_quote_dispatch import scenario

    captured = _patch_externals(monkeypatch)

    df = _make_dispatch_df(2)
    in_dir = tmp_path / "in"
    _write_input(in_dir, df)
    out = tmp_path / "out"
    scenario.run(input_dir=in_dir, output_dir=out)

    assert len(captured) == 2
    for msg in captured:
        attached_filenames = [
            part.get_filename() for part in msg.iter_attachments() if part.get_filename()
        ]
        assert any(name and name.endswith(".pdf") for name in attached_filenames), (
            f"no pdf attached: {attached_filenames!r}"
        )


def test_run_continues_when_pdf_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """일부 md_to_pdf 호출이 MdToPdfError → 첨부 없이 발송, built 여전히 증가."""
    from cases.case03_email_quote_dispatch import scenario
    from core.docgen import pdf as pdf_mod

    counter = {"n": 0}

    def flaky(md_path: Path | str, out_path: Path | str, **_kw: Any) -> None:
        counter["n"] += 1
        if counter["n"] in (2, 4):
            raise pdf_mod.MdToPdfError(f"simulated #{counter['n']}")
        Path(out_path).write_bytes(b"%PDF-1.4\n%stub")

    captured = _patch_externals(monkeypatch, pdf_fn=flaky)

    df = _make_dispatch_df(5)
    in_dir = tmp_path / "in"
    _write_input(in_dir, df)
    out = tmp_path / "out"
    result = scenario.run(input_dir=in_dir, output_dir=out)

    assert result["metrics"]["built"] == 5
    assert result["metrics"]["sent"] == 5
    assert result["metrics"]["errors"] == 0
    no_pdf_count = 0
    for msg in captured:
        names = [part.get_filename() or "" for part in msg.iter_attachments()]
        if not any(n.endswith(".pdf") for n in names):
            no_pdf_count += 1
    assert no_pdf_count == 2


def test_run_summary_transports_breakdown(
    dispatch_input_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """safe-fallback 50건 → transports['safe-fallback'] == 50."""
    from cases.case03_email_quote_dispatch import scenario

    _patch_externals(monkeypatch)

    result = scenario.run(input_dir=dispatch_input_dir, output_dir=tmp_path / "out")

    assert result["extras"]["transports"].get("safe-fallback") == 50


def test_run_with_zero_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """빈 입력 → 모든 카운트 0, 에러 없음."""
    from cases.case03_email_quote_dispatch import scenario

    _patch_externals(monkeypatch)

    df = pd.DataFrame(
        columns=[
            "거래처명",
            "담당자",
            "이메일",
            "견적번호",
            "품목요약",
            "예상금액",
            "과거거래",
        ]
    )
    in_dir = tmp_path / "in"
    _write_input(in_dir, df)
    result = scenario.run(input_dir=in_dir, output_dir=tmp_path / "out")

    assert result["metrics"]["built"] == 0
    assert result["metrics"]["sent"] == 0
    assert result["metrics"]["errors"] == 0
    assert result["extras"]["rows"] == []


def test_run_invalid_email_in_input_raises_per_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """한 row에 잘못된 이메일 → 해당 row만 errors+1, 나머지 정상 진행."""
    from cases.case03_email_quote_dispatch import scenario

    _patch_externals(monkeypatch)

    df = pd.DataFrame(
        [
            {
                "거래처명": "정상거래처",
                "담당자": "담당",
                "이메일": "ok@example.com",
                "견적번호": "Q-OK-001",
                "품목요약": "부품A",
                "예상금액": 10_000,
                "과거거래": "신규",
            },
            {
                "거래처명": "잘못거래처",
                "담당자": "담당",
                "이메일": "garbage",  # invalid
                "견적번호": "Q-BAD-002",
                "품목요약": "부품B",
                "예상금액": 20_000,
                "과거거래": "신규",
            },
            {
                "거래처명": "또정상",
                "담당자": "담당",
                "이메일": "fine@example.com",
                "견적번호": "Q-OK-003",
                "품목요약": "부품C",
                "예상금액": 30_000,
                "과거거래": "신규",
            },
        ]
    )
    in_dir = tmp_path / "in"
    _write_input(in_dir, df)

    result = scenario.run(input_dir=in_dir, output_dir=tmp_path / "out")

    assert result["metrics"]["built"] == 2
    assert result["metrics"]["sent"] == 2
    assert result["metrics"]["errors"] == 1


def test_run_personalization_includes_vendor_and_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """본문 텍스트에 vendor + history가 포함."""
    from cases.case03_email_quote_dispatch import scenario

    captured = _patch_externals(monkeypatch)

    df = pd.DataFrame(
        [
            {
                "거래처명": "유니크상사",
                "담당자": "박과장",
                "이메일": "to@example.com",
                "견적번호": "Q-PERS-001",
                "품목요약": "특별부품",
                "예상금액": 7_777_777,
                "과거거래": "히스토리-마커-X9Y",
            }
        ]
    )
    in_dir = tmp_path / "in"
    _write_input(in_dir, df)

    scenario.run(input_dir=in_dir, output_dir=tmp_path / "out")

    assert len(captured) == 1
    msg = captured[0]
    text_parts = [p.get_content() for p in msg.walk() if p.get_content_type() == "text/plain"]
    combined = "\n".join(text_parts)
    assert "유니크상사" in combined
    assert "히스토리-마커-X9Y" in combined


def test_run_uses_column_map_for_alternate_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """다른 컬럼명 입력 + column_map override (config["column_map"]) → 정상 처리."""
    from cases.case03_email_quote_dispatch import scenario

    captured = _patch_externals(monkeypatch)

    rows: list[dict[str, Any]] = [
        {
            "vendor_name": f"Customer-{i}",
            "contact_name": f"Person-{i}",
            "to_addr": f"c{i}@example.com",
            "quote_no_alt": f"R-{i:03d}",
            "summary_alt": f"item-{i}",
            "amt": 100_000 * i,
            "hist": f"history-{i}",
        }
        for i in range(1, 4)
    ]
    df = pd.DataFrame(rows)
    in_dir = tmp_path / "in"
    _write_input(in_dir, df)

    result = scenario.run(
        input_dir=in_dir,
        output_dir=tmp_path / "out",
        config={
            "column_map": {
                "vendor": "vendor_name",
                "contact": "contact_name",
                "to": "to_addr",
                "quote_no": "quote_no_alt",
                "summary": "summary_alt",
                "amount": "amt",
                "history": "hist",
            }
        },
    )

    assert result["metrics"]["built"] == 3
    assert result["metrics"]["sent"] == 3
    assert result["metrics"]["errors"] == 0
    assert len(captured) == 3


def test_run_summary_includes_pdf_failed_counter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T8.5 — metrics에 별도 ``pdf_failed`` 카운터 (시연 시 PDF 실패 가시)."""
    from cases.case03_email_quote_dispatch import scenario
    from core.docgen import pdf as pdf_mod

    counter = {"n": 0}

    def flaky(md_path: Path | str, out_path: Path | str, **_kw: Any) -> None:
        counter["n"] += 1
        if counter["n"] in (2, 4):
            raise pdf_mod.MdToPdfError(f"simulated #{counter['n']}")
        Path(out_path).write_bytes(b"%PDF-1.4\n%stub")

    _patch_externals(monkeypatch, pdf_fn=flaky)

    df = _make_dispatch_df(5)
    in_dir = tmp_path / "in"
    _write_input(in_dir, df)
    result = scenario.run(input_dir=in_dir, output_dir=tmp_path / "out")

    assert result["metrics"]["pdf_failed"] == 2
    assert result["metrics"]["built"] == 5
    assert result["metrics"]["sent"] == 5
    assert result["metrics"]["errors"] == 0


def test_run_summary_pdf_failed_zero_on_clean_run(
    dispatch_input_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T8.5 — 모든 PDF 정상 생성 시 ``pdf_failed == 0``."""
    from cases.case03_email_quote_dispatch import scenario

    _patch_externals(monkeypatch)
    result = scenario.run(input_dir=dispatch_input_dir, output_dir=tmp_path / "out")

    assert result["metrics"]["pdf_failed"] == 0


def test_run_handles_nan_amount(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """T8.5 — amount NaN → warning + amount_str='0', built+1."""
    from cases.case03_email_quote_dispatch import scenario

    captured = _patch_externals(monkeypatch)
    cap = _CaptureLogger()
    monkeypatch.setattr(scenario, "demo_logger", lambda _case: cap)

    df = pd.DataFrame(
        [
            {
                "거래처명": "정상",
                "담당자": "담당",
                "이메일": "ok@example.com",
                "견적번호": "Q-NAN-001",
                "품목요약": "부품",
                "예상금액": float("nan"),  # NaN 케이스
                "과거거래": "신규",
            },
            {
                "거래처명": "정상2",
                "담당자": "담당",
                "이메일": "ok2@example.com",
                "견적번호": "Q-NAN-002",
                "품목요약": "부품",
                "예상금액": 5_000,
                "과거거래": "신규",
            },
        ]
    )
    in_dir = tmp_path / "in"
    _write_input(in_dir, df)
    result = scenario.run(input_dir=in_dir, output_dir=tmp_path / "out")

    assert result["metrics"]["built"] == 2
    assert result["metrics"]["sent"] == 2
    assert result["metrics"]["errors"] == 0
    nan_warnings = [w for w in cap.warnings if "Q-NAN-001" in w and "NaN" in w]
    assert len(nan_warnings) == 1, f"expected NaN warning, got: {cap.warnings!r}"
    assert len(captured) == 2
    text_parts = [
        p.get_content() for p in captured[0].walk() if p.get_content_type() == "text/plain"
    ]
    assert any("0원" in t for t in text_parts), text_parts


def test_run_subject_contains_quote_no_and_vendor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """build_message subject에 quote_no + vendor 포함."""
    from cases.case03_email_quote_dispatch import scenario

    captured = _patch_externals(monkeypatch)

    df = pd.DataFrame(
        [
            {
                "거래처명": "타겟회사",
                "담당자": "담당",
                "이메일": "to@example.com",
                "견적번호": "Q-SUBJ-077",
                "품목요약": "부품",
                "예상금액": 1_000,
                "과거거래": "신규",
            }
        ]
    )
    in_dir = tmp_path / "in"
    _write_input(in_dir, df)

    scenario.run(input_dir=in_dir, output_dir=tmp_path / "out")

    assert len(captured) == 1
    subject = str(captured[0]["Subject"] or "")
    assert "Q-SUBJ-077" in subject
    assert "타겟회사" in subject
