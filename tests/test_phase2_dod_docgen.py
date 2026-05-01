"""Phase 2 DoD verification — docgen cases (case05/case06).

Integration-level checks that complement (not replace) the per-case tests in
``tests/test_case05_quote_generator.py`` and ``tests/test_case06_hwpx_form_filler.py``.

DoD criteria (per ``specs/2026-05-01-phase2-plan.md`` lines 1902-1911, adjusted
for plan v2 Deviation 2 — rhwp PoC failure):

- case05: docx + pdf 동시 생성 (per-request 1:1)
- case06: 양식 채우기 + extract_text 검증 (시각 미리보기는 운영자 한글 GUI 수동 확인)
- ``hwp_preview.render_preview`` 는 ``NotImplementedError`` 계약 유지 (Phase 3 deferred)
- case06 시나리오는 ``render_preview`` 를 호출하지 않는다 (T18 결정 잠금)
- ``core.docgen.template`` Jinja2 환경에서 StrictUndefined 동작
"""

from __future__ import annotations

import inspect
import zipfile
from pathlib import Path
from typing import Any

import jinja2
import pandas as pd
import pytest

# --- shared helpers --------------------------------------------------------


def _stub_pdf_ok(md_path: Path | str, out_path: Path | str, **_kw: Any) -> None:
    """md_to_pdf stub — DoD에서 npx 호출 없이 빈 %PDF 헤더 작성.

    PDF magic header (``%PDF``)를 그대로 써서 magic-byte 검증과 호환되게 한다.
    """
    Path(out_path).write_bytes(b"%PDF-1.4\n%dod-stub\n")


# --- case05 DoD: docx + pdf 동시 생성 -------------------------------------


@pytest.fixture
def case05_seed_input() -> Path:
    """Real 10-request seed used by case05 demo (42 rows). DoD requires this exact file."""
    p = Path("personas/sample_data/quote_requests.xlsx")
    if not p.exists():
        pytest.skip(f"DoD gap: seed file missing at {p}")
    return p


@pytest.fixture
def hwpx_template() -> Path:
    """case06 fixture; T16 PoC fallback path requires the prebuilt template to exist."""
    p = Path("personas/sample_data/forms/grant_application_template.hwpx")
    if not p.exists():
        pytest.skip(
            "DoD gap: grant_application_template.hwpx missing — "
            "run personas/scripts/build_grant_template.py"
        )
    return p


def test_case05_generates_docx_and_pdf(
    case05_seed_input: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DoD: case05 가 입력 시드(10 견적)에 대해 docx 와 pdf 를 동시에 생성.

    md_to_pdf 는 npx tsx 외부 호출이라 stub 으로 대체 (PDF magic 보존). docx는
    실제 ``python-docx`` 로 생성 — 외부 binary 의존 없음.
    """
    from cases.case05_doc_quote_generator import scenario
    from core.docgen import pdf as pdf_mod

    monkeypatch.setattr(pdf_mod, "md_to_pdf", _stub_pdf_ok)

    out = tmp_path / "out"
    summary = scenario.run(input_path=case05_seed_input, output_dir=out)

    assert summary["docx_count"] == 10, f"DoD gap: docx_count={summary['docx_count']}, expected 10"
    assert summary["pdf_count"] == 10, f"DoD gap: pdf_count={summary['pdf_count']}, expected 10"
    assert summary["errors"] == 0

    docx_files = sorted(out.glob("*.docx"))
    pdf_files = sorted(out.glob("*.pdf"))
    assert len(docx_files) == 10, f"DoD gap: {len(docx_files)} docx files on disk"
    assert len(pdf_files) == 10, f"DoD gap: {len(pdf_files)} pdf files on disk"


def test_case05_docx_is_valid_zip(
    case05_seed_input: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DoD: 생성된 docx 중 최소 1건이 valid ZIP 컨테이너 (docx == zip)."""
    from cases.case05_doc_quote_generator import scenario
    from core.docgen import pdf as pdf_mod

    monkeypatch.setattr(pdf_mod, "md_to_pdf", _stub_pdf_ok)

    out = tmp_path / "out"
    scenario.run(input_path=case05_seed_input, output_dir=out)

    docx_files = sorted(out.glob("*.docx"))
    assert docx_files, "DoD gap: no docx files produced"
    for path in docx_files:
        assert zipfile.is_zipfile(path), f"DoD gap: {path.name} is not a valid zip"


def test_case05_pdf_starts_with_pdf_magic(
    case05_seed_input: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DoD: 생성된 pdf 중 최소 1건이 ``%PDF`` magic header 로 시작.

    stub 이 ``b"%PDF-1.4..."`` 로 작성하므로 첫 4바이트가 ``b"%PDF"`` 여야 한다.
    실제 npx 사용 시에도 동일 magic 이 보장된다 (PDF 1.x 표준).
    """
    from cases.case05_doc_quote_generator import scenario
    from core.docgen import pdf as pdf_mod

    monkeypatch.setattr(pdf_mod, "md_to_pdf", _stub_pdf_ok)

    out = tmp_path / "out"
    scenario.run(input_path=case05_seed_input, output_dir=out)

    pdf_files = sorted(out.glob("*.pdf"))
    assert pdf_files, "DoD gap: no pdf files produced"
    for path in pdf_files:
        with path.open("rb") as f:
            head = f.read(4)
        assert head == b"%PDF", f"DoD gap: {path.name} missing %PDF magic header (got {head!r})"


def test_case05_processes_all_quote_requests(
    case05_seed_input: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DoD: 시드의 unique 견적번호 수만큼 ``summary['requests']`` 가 채워짐.

    seed 가 10 견적 × 4.2 평균 품목 ≈ 42 행. 시나리오는 견적번호로 group →
    requests 리스트 항목 수 = 10. 갯수가 줄어들면 즉시 DoD 위반.
    """
    from cases.case05_doc_quote_generator import scenario
    from core.docgen import pdf as pdf_mod

    monkeypatch.setattr(pdf_mod, "md_to_pdf", _stub_pdf_ok)

    df = pd.read_excel(case05_seed_input)
    expected_requests = int(df["견적번호"].nunique())
    assert expected_requests == 10, (
        f"DoD gap: seed unique 견적번호 = {expected_requests} (expected 10)"
    )

    out = tmp_path / "out"
    summary = scenario.run(input_path=case05_seed_input, output_dir=out)

    assert len(summary["requests"]) == expected_requests, (
        f"DoD gap: requests={len(summary['requests'])}, expected {expected_requests}"
    )
    for entry in summary["requests"]:
        for key in ("request_id", "vendor", "n_items"):
            assert key in entry, f"DoD gap: requests entry missing key {key!r}"
        assert int(entry["n_items"]) >= 1


# --- case06 DoD: 양식 채우기 + 미리보기 (rhwp 실패 fallback) ----------------


def test_case06_fills_grant_application(
    hwpx_template: Path,
    tmp_path: Path,
) -> None:
    """DoD: case06 가 8 필드 GrantApplication → .hwpx 생성 + 모든 값이 본문에 포함.

    fixture 가 없으면 skip. 외부 API 미사용이라 safe_mode 무관.
    """
    from cases.case06_hwpx_govt_form_filler import scenario
    from core.docgen import hwpx as hwpx_mod
    from personas.sample_data.grant_data import AX_TRADING_GRANT

    summary = scenario.run(template_path=hwpx_template, output_dir=tmp_path)

    out_path = Path(summary["output_path"])
    assert out_path.exists(), f"DoD gap: output .hwpx missing at {out_path}"
    assert out_path.suffix == ".hwpx"
    assert out_path.stat().st_size > 0
    assert zipfile.is_zipfile(out_path), f"DoD gap: {out_path.name} is not a valid zip"

    assert summary["fields_filled"] == 8
    assert summary["verification_passed"] is True
    assert summary["missing_values"] == []

    # extract_text 로 8 필드 값(표시 형식 적용 후) 모두 포함 확인.
    text = hwpx_mod.extract_text(out_path)
    assert AX_TRADING_GRANT["company_name"] in text
    assert AX_TRADING_GRANT["ceo_name"] in text
    assert AX_TRADING_GRANT["biznum"] in text
    assert AX_TRADING_GRANT["business_area"] in text
    assert f"{AX_TRADING_GRANT['grant_amount']:,}원" in text
    assert f"{AX_TRADING_GRANT['annual_revenue']:,}원" in text
    assert f"{AX_TRADING_GRANT['employee_count']}명" in text
    assert AX_TRADING_GRANT["application_date"] in text


def test_case06_render_preview_remains_unimplemented(tmp_path: Path) -> None:
    """DoD: ``hwp_preview.render_preview`` 는 Phase 3 deferred — 호출 시 ``NotImplementedError``.

    Plan v2 Deviation 2 (T16 PoC 실패) 잠금. 메시지에 결정 문서 위치와
    Phase 3 기재가 남아있어야 운영자가 즉시 진단 가능하다.
    """
    from core.docgen import hwp_preview

    placeholder = tmp_path / "any.hwpx"
    placeholder.write_bytes(b"")  # 호출 도달 전에 NotImplementedError 가 떠야 한다.

    with pytest.raises(NotImplementedError) as excinfo:
        hwp_preview.render_preview(placeholder)

    msg = str(excinfo.value)
    assert "Phase 3" in msg, f"DoD gap: NotImplementedError missing Phase 3 marker: {msg!r}"
    assert "rhwp-poc-decision.md" in msg, (
        f"DoD gap: NotImplementedError missing decision doc reference: {msg!r}"
    )


def test_case06_scenario_does_not_call_render_preview() -> None:
    """DoD: case06 ``scenario.run`` 소스에 ``render_preview(`` 호출이 없어야 한다.

    plan v2 Deviation 2 결정 잠금: rhwp PoC 실패 → preview 자동화 deferred.
    이 테스트가 실패하면 누군가 fallback 결정을 무시하고 시나리오에 preview
    호출을 다시 끼워넣은 것 → 즉시 차단.
    """
    from cases.case06_hwpx_govt_form_filler import scenario

    src = inspect.getsource(scenario)
    assert "render_preview(" not in src, (
        "DoD gap: case06 scenario calls render_preview() — "
        "Plan v2 Deviation 2 prohibits it (rhwp PoC failed, see specs/rhwp-poc-decision.md)"
    )


def test_case06_demo_logger_emits_hangul_gui_guidance(
    hwpx_template: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DoD: case06 실행 중 데모 로그에 한글 GUI 수동 확인 안내 문구가 포함.

    rhwp 자동 미리보기가 없는 만큼 운영자가 한글에서 직접 열어봐야 함을
    명확히 알려줘야 한다 (시연 운영 안전장치).
    """

    class _CaptureLogger:
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

    from cases.case06_hwpx_govt_form_filler import scenario

    cap = _CaptureLogger()
    monkeypatch.setattr(scenario, "demo_logger", lambda _case: cap)

    scenario.run(template_path=hwpx_template, output_dir=tmp_path)

    combined = "\n".join(cap.infos + cap.successes + cap.warnings)
    # "한글" 문자열 또는 "Hancom" 영문 표기 중 하나는 반드시 등장.
    assert "한글" in combined or "Hancom" in combined, (
        f"DoD gap: no 한글 GUI guidance in demo logger output: {combined!r}"
    )


# --- template StrictUndefined 검증 ----------------------------------------


def test_template_strict_undefined_raises_on_missing_var() -> None:
    """DoD: ``render_html_string`` 이 누락 변수에 ``UndefinedError`` 를 raise.

    ``core/docgen/template.py`` 의 Jinja2 환경이 StrictUndefined 로 구성되어
    누락 변수를 즉시 노출해야 한다. (silent empty-string 채움 방지 — case03
    메일 본문에서 placeholder 가 누락되면 발송 전에 실패해야 한다.)
    """
    from core.docgen import template

    with pytest.raises(jinja2.UndefinedError):
        template.render_html_string("{{ unknown }}", {})

    # 일반 (non-HTML) 환경도 동일 동작.
    with pytest.raises(jinja2.UndefinedError):
        template.render_string("{{ unknown }}", {})


def test_template_renders_with_full_context() -> None:
    """DoD: 컨텍스트가 충분하면 정상 렌더 — StrictUndefined 가 정상 입력은 차단하지 않음."""
    from core.docgen import template

    rendered_text = template.render_string(
        "Hello {{ name }}, total {{ amount }}원",
        {"name": "박과장", "amount": 1_500_000},
    )
    assert rendered_text == "Hello 박과장, total 1500000원"

    rendered_html = template.render_html_string(
        "<p>{{ greeting }}</p>",
        {"greeting": "안녕하세요"},
    )
    assert rendered_html == "<p>안녕하세요</p>"
