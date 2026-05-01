"""Tests for case05 — 견적서/거래명세서 자동 생성 (docx + pdf)."""

from pathlib import Path
from typing import Any

import pandas as pd
import pytest


class _CaptureLogger:
    """In-memory logger that captures messages by level — used to assert per-request log lines."""

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


def _stub_pdf(md_path: Path | str, out_path: Path | str, **_kw: Any) -> None:
    """md_to_pdf mock — 실제 npx 호출 없이 빈 PDF stub 작성."""
    Path(out_path).write_bytes(b"%PDF-1.4\n%stub")


def _make_quote_df(n_requests: int = 10, items_per: int = 4) -> pd.DataFrame:
    """헬퍼: 표준 스키마 입력 DataFrame 생성."""
    rows: list[dict[str, Any]] = []
    for i in range(1, n_requests + 1):
        for j in range(items_per):
            rows.append(
                {
                    "견적번호": f"Q-2026-{i:03d}",
                    "거래처명": f"거래처{i:02d}",
                    "담당자": f"담당자{i}",
                    "이메일": f"v{i}@example.com",
                    "품목": f"부품-{i}-{j}",
                    "수량": 10 + j,
                    "단가": 50_000 + j * 1_000,
                    "납기일": "2026-06-30",
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture
def quote_input(tmp_path: Path) -> Path:
    """10 requests × 4 items = 40 rows (standard column schema)."""
    df = _make_quote_df(n_requests=10, items_per=4)
    p = tmp_path / "quote_requests.xlsx"
    df.to_excel(p, index=False)
    return p


def test_run_creates_docx_and_pdf_per_request(
    quote_input: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """10 견적번호 시드 → docx 10개 + pdf 10개."""
    from cases.case05_doc_quote_generator import scenario
    from core.docgen import pdf as pdf_mod

    monkeypatch.setattr(pdf_mod, "md_to_pdf", _stub_pdf)
    out = tmp_path / "out"

    summary = scenario.run(input_path=quote_input, output_dir=out)

    assert summary["docx_count"] == 10
    assert summary["pdf_count"] == 10
    assert summary["errors"] == 0
    docx_files = list(out.glob("*.docx"))
    pdf_files = list(out.glob("*.pdf"))
    assert len(docx_files) == 10
    assert len(pdf_files) == 10


def test_run_pdf_failure_does_not_block_other_requests(
    quote_input: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """일부 md_to_pdf 호출이 MdToPdfError → docx 모두 생성, pdf 일부만, errors >= 1."""
    from cases.case05_doc_quote_generator import scenario
    from core.docgen import pdf as pdf_mod

    counter = {"n": 0}

    def flaky(md_path: Path | str, out_path: Path | str, **_kw: Any) -> None:
        counter["n"] += 1
        if counter["n"] in (3, 7):
            raise pdf_mod.MdToPdfError(f"simulated failure #{counter['n']}")
        Path(out_path).write_bytes(b"%PDF-1.4\n%stub")

    monkeypatch.setattr(pdf_mod, "md_to_pdf", flaky)
    out = tmp_path / "out"

    summary = scenario.run(input_path=quote_input, output_dir=out)

    assert summary["docx_count"] == 10  # word.build_quote 모두 성공
    assert summary["pdf_count"] == 8  # 2건 실패
    assert summary["errors"] >= 1


def test_run_uses_column_map_for_alternate_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """다른 입력 컬럼 스키마 + column_map override → 정상 처리."""
    from cases.case05_doc_quote_generator import scenario
    from core.docgen import pdf as pdf_mod

    monkeypatch.setattr(pdf_mod, "md_to_pdf", _stub_pdf)

    rows: list[dict[str, Any]] = []
    for i in range(1, 4):
        for j in range(3):
            rows.append(
                {
                    "request_no": f"R-{i}",
                    "customer": f"Customer-{i}",
                    "product": f"prod-{j}",
                    "units": 5,
                    "unit_price": 100_000,
                    "delivery": "2026-07-01",
                }
            )
    df = pd.DataFrame(rows)
    inp = tmp_path / "alt.xlsx"
    df.to_excel(inp, index=False)

    out = tmp_path / "out"
    summary = scenario.run(
        input_path=inp,
        output_dir=out,
        column_map={
            "request_id": "request_no",
            "vendor": "customer",
            "name": "product",
            "qty": "units",
            "price": "unit_price",
            "due_date": "delivery",
        },
    )

    assert summary["docx_count"] == 3
    assert summary["pdf_count"] == 3
    assert summary["errors"] == 0


def test_run_with_zero_requests(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """빈 입력 → summary 모두 0."""
    from cases.case05_doc_quote_generator import scenario
    from core.docgen import pdf as pdf_mod

    monkeypatch.setattr(pdf_mod, "md_to_pdf", _stub_pdf)

    df = pd.DataFrame(
        columns=["견적번호", "거래처명", "담당자", "이메일", "품목", "수량", "단가", "납기일"]
    )
    inp = tmp_path / "empty.xlsx"
    df.to_excel(inp, index=False)
    out = tmp_path / "out"

    summary = scenario.run(input_path=inp, output_dir=out)

    assert summary["docx_count"] == 0
    assert summary["pdf_count"] == 0
    assert summary["errors"] == 0
    assert summary["requests"] == []


def test_run_summary_structure(
    quote_input: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """summary key 보장 + requests 항목 구조."""
    from cases.case05_doc_quote_generator import scenario
    from core.docgen import pdf as pdf_mod

    monkeypatch.setattr(pdf_mod, "md_to_pdf", _stub_pdf)
    out = tmp_path / "out"

    summary = scenario.run(input_path=quote_input, output_dir=out)

    for key in ("docx_count", "pdf_count", "errors", "requests"):
        assert key in summary, f"missing key: {key}"
    assert isinstance(summary["requests"], list)
    assert len(summary["requests"]) == 10
    for entry in summary["requests"]:
        assert "request_id" in entry
        assert "vendor" in entry
        assert "n_items" in entry
        assert isinstance(entry["n_items"], int)
        assert entry["n_items"] >= 1


def test_run_creates_output_dir_if_missing(
    quote_input: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """output_dir 미존재 → 자동 생성."""
    from cases.case05_doc_quote_generator import scenario
    from core.docgen import pdf as pdf_mod

    monkeypatch.setattr(pdf_mod, "md_to_pdf", _stub_pdf)

    target = tmp_path / "nested" / "deeper" / "out"
    assert not target.exists()

    summary = scenario.run(input_path=quote_input, output_dir=target)

    assert target.exists()
    assert target.is_dir()
    assert summary["docx_count"] == 10


def test_run_docx_contains_vendor_and_items(
    quote_input: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """결과 docx 1건 → vendor명 + 품목명 + '견적번호' 포함."""
    from docx import Document

    from cases.case05_doc_quote_generator import scenario
    from core.docgen import pdf as pdf_mod

    monkeypatch.setattr(pdf_mod, "md_to_pdf", _stub_pdf)
    out = tmp_path / "out"

    scenario.run(input_path=quote_input, output_dir=out)

    docx_files = sorted(out.glob("*.docx"))
    assert docx_files, "no docx generated"
    target = docx_files[0]
    doc = Document(str(target))
    full_text = "\n".join(p.text for p in doc.paragraphs)
    table_text = "\n".join(
        cell.text for tbl in doc.tables for row in tbl.rows for cell in row.cells
    )
    combined = full_text + "\n" + table_text

    assert "거래처01" in combined  # vendor
    assert "견적번호" in combined  # label
    # at least 1 품목 (품목명 prefix from fixture)
    assert "부품-1-" in combined


def test_run_continues_after_word_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """일부 word.build_quote 실패 → 다른 견적은 정상 진행."""
    from cases.case05_doc_quote_generator import scenario
    from core.docgen import pdf as pdf_mod
    from core.docgen import word as word_mod

    monkeypatch.setattr(pdf_mod, "md_to_pdf", _stub_pdf)

    real_build = word_mod.build_quote
    counter = {"n": 0}

    def flaky_build(**kwargs: Any) -> None:
        counter["n"] += 1
        if counter["n"] == 2:
            raise ValueError("simulated word failure")
        real_build(**kwargs)

    monkeypatch.setattr(word_mod, "build_quote", flaky_build)

    df = _make_quote_df(n_requests=4, items_per=3)
    inp = tmp_path / "in.xlsx"
    df.to_excel(inp, index=False)
    out = tmp_path / "out"

    summary = scenario.run(input_path=inp, output_dir=out)

    assert summary["docx_count"] == 3  # 1건 실패
    assert summary["errors"] >= 1
    # other 3 requests should still have been attempted (and pdf built for those)
    assert summary["pdf_count"] >= 3


def test_run_logs_per_request_progress(
    quote_input: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """10 견적 입력 → per-request info 로그가 견적번호 + vendor + 품목 수 포함."""
    from cases.case05_doc_quote_generator import scenario
    from core.docgen import pdf as pdf_mod

    monkeypatch.setattr(pdf_mod, "md_to_pdf", _stub_pdf)

    cap = _CaptureLogger()
    monkeypatch.setattr(scenario, "demo_logger", lambda _case: cap)

    out = tmp_path / "out"
    summary = scenario.run(input_path=quote_input, output_dir=out)

    assert summary["docx_count"] == 10
    # at least 10 info lines for 10 requests
    request_lines = [m for m in cap.infos if "Q-2026-" in m]
    assert len(request_lines) == 10, f"expected 10 progress lines, got {len(request_lines)}"
    # each line should include the vendor name (거래처NN) and item count (4개)
    sample = request_lines[0]
    assert "Q-2026-001" in sample
    assert "거래처01" in sample
    assert "4" in sample  # items_per=4


def test_run_progress_log_escapes_markup_in_vendor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """vendor가 markup-like 패턴을 포함 → rich.markup.escape 흔적이 로그에 보임 (lessons L10).

    rich.markup.escape는 ASCII 마크업 태그처럼 보이는 패턴만 escape한다 (Korean 내부
    bracket은 이미 안전). 따라서 실제로 markup으로 해석될 위험이 있는 패턴만 검증.
    """
    from cases.case05_doc_quote_generator import scenario
    from core.docgen import pdf as pdf_mod

    monkeypatch.setattr(pdf_mod, "md_to_pdf", _stub_pdf)

    rows: list[dict[str, Any]] = [
        {
            "견적번호": "Q-X-001",
            "거래처명": "[bold]회사[/bold]",
            "담당자": "담당",
            "이메일": "x@example.com",
            "품목": "부품-1",
            "수량": 1,
            "단가": 10_000,
            "납기일": "2026-06-30",
        }
    ]
    df = pd.DataFrame(rows)
    inp = tmp_path / "bracket.xlsx"
    df.to_excel(inp, index=False)

    cap = _CaptureLogger()
    monkeypatch.setattr(scenario, "demo_logger", lambda _case: cap)

    out = tmp_path / "out"
    scenario.run(input_path=inp, output_dir=out)

    # Find the progress info line for this request
    progress = [m for m in cap.infos if "Q-X-001" in m]
    assert progress, f"no progress log found, infos={cap.infos!r}"
    line = progress[0]
    # Escaped form: rich.markup.escape inserts backslash before [bold] and [/bold].
    assert "\\[bold]" in line, f"expected escaped bracket form in: {line!r}"
    assert "\\[/bold]" in line, f"expected escaped closing tag in: {line!r}"


def test_run_skips_empty_vendor_with_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """vendor 빈 문자열 견적 → skip + warning(request_id 포함) + summary['errors'] += 1."""
    from cases.case05_doc_quote_generator import scenario
    from core.docgen import pdf as pdf_mod

    monkeypatch.setattr(pdf_mod, "md_to_pdf", _stub_pdf)

    rows: list[dict[str, Any]] = []
    # request 1: empty vendor
    rows.append(
        {
            "견적번호": "Q-EMPTY-001",
            "거래처명": "",
            "담당자": "x",
            "이메일": "x@example.com",
            "품목": "부품-1",
            "수량": 1,
            "단가": 10_000,
            "납기일": "2026-06-30",
        }
    )
    # request 2: normal
    rows.append(
        {
            "견적번호": "Q-OK-002",
            "거래처명": "정상거래처",
            "담당자": "y",
            "이메일": "y@example.com",
            "품목": "부품-2",
            "수량": 2,
            "단가": 20_000,
            "납기일": "2026-06-30",
        }
    )
    df = pd.DataFrame(rows)
    inp = tmp_path / "mixed.xlsx"
    df.to_excel(inp, index=False)

    cap = _CaptureLogger()
    monkeypatch.setattr(scenario, "demo_logger", lambda _case: cap)

    out = tmp_path / "out"
    summary = scenario.run(input_path=inp, output_dir=out)

    assert summary["docx_count"] == 1  # only Q-OK-002 created
    assert summary["errors"] >= 1
    # warning should mention request_id
    matched = [w for w in cap.warnings if "Q-EMPTY-001" in w]
    assert matched, f"expected warning mentioning Q-EMPTY-001, got {cap.warnings!r}"


def test_run_skips_whitespace_vendor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """vendor가 공백만(\"   \")인 견적도 동일하게 skip."""
    from cases.case05_doc_quote_generator import scenario
    from core.docgen import pdf as pdf_mod

    monkeypatch.setattr(pdf_mod, "md_to_pdf", _stub_pdf)

    rows: list[dict[str, Any]] = [
        {
            "견적번호": "Q-WS-001",
            "거래처명": "   ",
            "담당자": "x",
            "이메일": "x@example.com",
            "품목": "부품-1",
            "수량": 1,
            "단가": 10_000,
            "납기일": "2026-06-30",
        },
        {
            "견적번호": "Q-OK-002",
            "거래처명": "정상거래처",
            "담당자": "y",
            "이메일": "y@example.com",
            "품목": "부품-2",
            "수량": 2,
            "단가": 20_000,
            "납기일": "2026-06-30",
        },
    ]
    df = pd.DataFrame(rows)
    inp = tmp_path / "ws.xlsx"
    df.to_excel(inp, index=False)

    cap = _CaptureLogger()
    monkeypatch.setattr(scenario, "demo_logger", lambda _case: cap)

    out = tmp_path / "out"
    summary = scenario.run(input_path=inp, output_dir=out)

    assert summary["docx_count"] == 1
    assert summary["errors"] >= 1
    matched = [w for w in cap.warnings if "Q-WS-001" in w]
    assert matched, f"expected warning mentioning Q-WS-001, got {cap.warnings!r}"


def test_run_error_log_contains_request_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """word.build_quote가 raise → warning 로그에 request_id + 예외 타입 포함."""
    from cases.case05_doc_quote_generator import scenario
    from core.docgen import pdf as pdf_mod
    from core.docgen import word as word_mod

    monkeypatch.setattr(pdf_mod, "md_to_pdf", _stub_pdf)

    real_build = word_mod.build_quote
    counter = {"n": 0}

    def flaky_build(**kwargs: Any) -> None:
        counter["n"] += 1
        if counter["n"] == 2:
            raise RuntimeError("boom")
        real_build(**kwargs)

    monkeypatch.setattr(word_mod, "build_quote", flaky_build)

    cap = _CaptureLogger()
    monkeypatch.setattr(scenario, "demo_logger", lambda _case: cap)

    df = _make_quote_df(n_requests=3, items_per=2)
    inp = tmp_path / "in.xlsx"
    df.to_excel(inp, index=False)
    out = tmp_path / "out"

    summary = scenario.run(input_path=inp, output_dir=out)

    assert summary["errors"] >= 1
    # the failed request id is the 2nd: Q-2026-002
    matched = [w for w in cap.warnings if "Q-2026-002" in w and "RuntimeError" in w]
    assert matched, f"expected warning with request_id and RuntimeError, got {cap.warnings!r}"
