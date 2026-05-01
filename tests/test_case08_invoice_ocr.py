"""T15: case08 — 세금계산서 일괄 OCR → 회계 CSV.

``core.ocr.invoice.extract`` mock 기반 contract 검증. 실제 Ollama 호출 없음.
seed 30장은 ``personas/sample_data/invoices_scanned/`` 에 미리 생성돼 있어야 한다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from PIL import Image

from cases.case08_ocr_invoice_to_csv import scenario
from core.ocr import invoice
from core.ocr.invoice import InvoiceData

# 알고리즘 검증된 known-valid 공개 사업자번호 (test_ocr_invoice.py와 동일).
_VALID_SUPPLIER = "220-81-62517"  # 삼성전자
_VALID_BUYER = "120-81-47521"  # 카카오


def _make_blank_png(path: Path) -> None:
    Image.new("RGB", (10, 10), "white").save(path)


def _make_invoice_data(
    *,
    invoice_no: str = "INV-2026-00001",
    issue_date: str = "2026-04-01",
    supplier_biznum: str = _VALID_SUPPLIER,
    buyer_biznum: str = _VALID_BUYER,
    supplier_name: str = "공급자(주)",
    buyer_name: str = "공급받는자(주)",
    total_supply: int = 1_000_000,
    total_vat: int = 100_000,
    total_amount: int = 1_100_000,
) -> InvoiceData:
    return InvoiceData(
        invoice_no=invoice_no,
        issue_date=issue_date,
        supplier_biznum=supplier_biznum,
        supplier_name=supplier_name,
        buyer_biznum=buyer_biznum,
        buyer_name=buyer_name,
        line_items=[],
        total_supply=total_supply,
        total_vat=total_vat,
        total_amount=total_amount,
    )


def _mock_invoice(
    monkeypatch: pytest.MonkeyPatch,
    response: InvoiceData | None = None,
    fail_filenames: tuple[str, ...] = (),
    invalid_biznum_filenames: tuple[str, ...] = (),
) -> list[Path]:
    """``invoice.extract`` mock.

    Args:
        response: 기본 InvoiceData (None이면 valid 1건).
        fail_filenames: ValueError raise 할 파일.
        invalid_biznum_filenames: 응답 자체는 성공하지만 supplier_biznum이 invalid.
    """
    calls: list[Path] = []
    default = response or _make_invoice_data()

    def _fake(image_path: Path | str) -> InvoiceData:
        p = Path(image_path)
        calls.append(p)
        if p.name in fail_filenames:
            raise ValueError(f"mock OCR failure for {p.name}")
        if p.name in invalid_biznum_filenames:
            return _make_invoice_data(supplier_biznum="123-45-67890")  # 체크섬 fail
        return default

    monkeypatch.setattr(invoice, "extract", _fake)
    return calls


# -- 1. deterministic safe mode --------------------------------------------


def test_scenario_runs_safe_mode_returns_deterministic_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """safe-mode 두 번 실행 → elapsed_seconds 제외 핵심 키 동일."""
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    for i in range(3):
        _make_blank_png(input_dir / f"inv_{i:03d}.png")

    _mock_invoice(monkeypatch)
    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"

    summary1 = scenario.run(input_dir=input_dir, output_dir=out1)
    summary2 = scenario.run(input_dir=input_dir, output_dir=out2)

    # 핵심 invariants — elapsed_seconds와 per_image_ms는 시간 의존이라 제외.
    assert summary1["processed"] == summary2["processed"] == 3
    assert summary1["verified"] == summary2["verified"] == 3
    assert summary1["failed"] == summary2["failed"] == 0
    assert summary1["failures"] == summary2["failures"] == []

    # CSV 내용도 동일해야 한다 (deterministic input mock).
    assert (out1 / "invoices_utf8.csv").read_bytes() == (out2 / "invoices_utf8.csv").read_bytes()
    assert (out1 / "invoices_cp949.csv").read_bytes() == (out2 / "invoices_cp949.csv").read_bytes()


# -- 2. dual CSV outputs ----------------------------------------------------


def test_scenario_creates_both_csv_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    _make_blank_png(input_dir / "inv_001.png")

    _mock_invoice(monkeypatch)
    out_dir = tmp_path / "out"
    summary = scenario.run(input_dir=input_dir, output_dir=out_dir)

    utf8_path = out_dir / "invoices_utf8.csv"
    cp949_path = out_dir / "invoices_cp949.csv"
    assert utf8_path.exists()
    assert cp949_path.exists()
    assert str(utf8_path) in summary["outputs"]
    assert str(cp949_path) in summary["outputs"]

    # utf-8 BOM 확인 (utf-8-sig).
    with utf8_path.open("rb") as f:
        assert f.read(3) == b"\xef\xbb\xbf"
    # cp949는 BOM 없음.
    with cp949_path.open("rb") as f:
        assert f.read(3) != b"\xef\xbb\xbf"
    # cp949 인코딩으로 읽을 수 있어야 한다.
    cp949_text = cp949_path.read_text(encoding="cp949")
    assert "거래일" in cp949_text


# -- 3. verified vs failed split -------------------------------------------


def test_scenario_separates_verified_from_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    for i in range(5):
        _make_blank_png(input_dir / f"inv_{i:03d}.png")

    # inv_001: extract raises (OCR 실패).
    # inv_003: post-validation에서 supplier_biznum 체크섬 fail.
    _mock_invoice(
        monkeypatch,
        fail_filenames=("inv_001.png",),
        invalid_biznum_filenames=("inv_003.png",),
    )

    out_dir = tmp_path / "out"
    summary = scenario.run(input_dir=input_dir, output_dir=out_dir)

    assert summary["processed"] == 5
    assert summary["verified"] == 3
    assert summary["failed"] == 2

    failures_path = out_dir / "validation_failures.json"
    assert failures_path.exists()
    failures = json.loads(failures_path.read_text(encoding="utf-8"))
    filenames = {f["filename"] for f in failures}
    assert filenames == {"inv_001.png", "inv_003.png"}
    stages = {f["stage"] for f in failures}
    assert stages == {"extract", "validate"}


def test_scenario_writes_empty_failures_when_all_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """실패 0건이어도 validation_failures.json은 작성 (빈 리스트)."""
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    _make_blank_png(input_dir / "inv_001.png")
    _mock_invoice(monkeypatch)

    out_dir = tmp_path / "out"
    summary = scenario.run(input_dir=input_dir, output_dir=out_dir)

    failures_path = out_dir / "validation_failures.json"
    assert failures_path.exists()
    assert json.loads(failures_path.read_text(encoding="utf-8")) == []
    assert summary["failed"] == 0


# -- 4. processes all seeds (real seeds on disk) ---------------------------


def test_scenario_processes_all_seeds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """personas/sample_data/invoices_scanned/ 전체를 처리한다."""
    seed_dir = Path("personas/sample_data/invoices_scanned")
    if not seed_dir.exists():
        pytest.skip("invoices_scanned seed missing — run generate_invoices.py first")
    seed_count = sum(
        1
        for p in seed_dir.iterdir()
        if p.is_file() and p.suffix.lower() in {".png", ".jpg"} and not p.name.startswith("_")
    )

    _mock_invoice(monkeypatch)
    out_dir = tmp_path / "out"
    summary = scenario.run(input_dir=seed_dir, output_dir=out_dir)

    assert summary["processed"] == seed_count
    assert seed_count >= 30  # T15 요구: 30장 이상.


# -- 5. meta.yaml 구조 ------------------------------------------------------


def test_scenario_meta_yaml_loads() -> None:
    meta_path = Path("cases/case08_ocr_invoice_to_csv/meta.yaml")
    assert meta_path.exists()
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    assert meta["id"] == "case08_ocr_invoice_to_csv"
    assert meta["category"] == "ocr"
    assert "ollama_gemma" in meta["external_apis"]
    assert "1min" in meta["demo_lengths"]
    assert meta["persona"] == "박과장"


# -- 6. underscore prefix 스킵 ----------------------------------------------


def test_scenario_skips_underscore_prefix_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    _make_blank_png(input_dir / "inv_001.png")
    _make_blank_png(input_dir / "inv_002.png")
    _make_blank_png(input_dir / "_temp.png")
    (input_dir / "_ground_truth.json").write_text("[]", encoding="utf-8")

    _mock_invoice(monkeypatch)
    out_dir = tmp_path / "out"
    summary = scenario.run(input_dir=input_dir, output_dir=out_dir)
    assert summary["processed"] == 2


# -- 7. personas fallback ---------------------------------------------------


def test_scenario_uses_personas_fallback_when_input_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()
    for i in range(3):
        _make_blank_png(seed_dir / f"inv_{i:03d}.png")
    monkeypatch.setattr(scenario, "_DEFAULT_FALLBACK_DIR", seed_dir)

    _mock_invoice(monkeypatch)
    out_dir = tmp_path / "out"
    summary = scenario.run(input_dir=None, output_dir=out_dir)

    assert summary["processed"] == 3


# -- 8. 면세 거래 통과 ------------------------------------------------------


def test_scenario_accepts_tax_free_invoice(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """vat=0 (면세) 거래도 verified로 통과한다."""
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    _make_blank_png(input_dir / "inv_001.png")

    tax_free = _make_invoice_data(total_supply=500_000, total_vat=0, total_amount=500_000)
    _mock_invoice(monkeypatch, response=tax_free)

    out_dir = tmp_path / "out"
    summary = scenario.run(input_dir=input_dir, output_dir=out_dir)
    assert summary["verified"] == 1
    assert summary["failed"] == 0


# -- 9. _classify_failure 단위 검증 -----------------------------------------


def test_classify_failure_passes_valid() -> None:
    data = _make_invoice_data()
    assert scenario._classify_failure(data) is None


def test_classify_failure_invalid_supplier_biznum() -> None:
    data = _make_invoice_data(supplier_biznum="123-45-67890")
    reason = scenario._classify_failure(data)
    assert reason is not None
    assert "supplier_biznum" in reason


def test_classify_failure_invalid_buyer_biznum() -> None:
    data = _make_invoice_data(buyer_biznum="123-45-67890")
    reason = scenario._classify_failure(data)
    assert reason is not None
    assert "buyer_biznum" in reason


def test_classify_failure_vat_mismatch() -> None:
    # vat이 0도 아니고 supply // 10도 아닌 경우.
    data = _make_invoice_data(total_supply=1_000_000, total_vat=99_999)
    reason = scenario._classify_failure(data)
    assert reason is not None
    assert "vat mismatch" in reason


def test_classify_failure_tax_free_passes() -> None:
    """vat=0은 면세로 간주 → 통과."""
    data = _make_invoice_data(total_supply=1_000_000, total_vat=0, total_amount=1_000_000)
    assert scenario._classify_failure(data) is None


# -- 10. per-image timer + summary 구조 ------------------------------------


def test_scenario_summary_includes_per_image_ms(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    for i in range(4):
        _make_blank_png(input_dir / f"inv_{i:03d}.png")

    _mock_invoice(monkeypatch)
    out_dir = tmp_path / "out"
    summary = scenario.run(input_dir=input_dir, output_dir=out_dir)

    per_image: list[dict[str, Any]] = summary["per_image_ms"]
    assert len(per_image) == 4
    for entry in per_image:
        assert "filename" in entry
        assert "elapsed_ms" in entry
        assert isinstance(entry["elapsed_ms"], float)
    assert "elapsed_seconds" in summary
    assert isinstance(summary["elapsed_seconds"], float)


# -- 11. 빈 디렉토리 --------------------------------------------------------


def test_scenario_zero_invoices(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    empty_seed = tmp_path / "empty"
    empty_seed.mkdir()
    monkeypatch.setattr(scenario, "_DEFAULT_FALLBACK_DIR", empty_seed)

    _mock_invoice(monkeypatch)
    out_dir = tmp_path / "out"
    summary = scenario.run(input_dir=input_dir, output_dir=out_dir)
    assert summary["processed"] == 0
    # CSV는 헤더만 작성, JSON은 빈 리스트.
    utf8_text = (out_dir / "invoices_utf8.csv").read_text(encoding="utf-8-sig")
    assert "거래일" in utf8_text
    assert utf8_text.count("\n") == 1


# -- 12. CSV 컬럼 ------------------------------------------------------------


# -- 13. T15.5: 품질 경고 (failure_rate >= 50%) ----------------------------


def test_scenario_warns_on_high_failure_rate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """>=50% 실패 시 quality_warning=True + failure_rate 정확."""
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    for i in range(4):
        _make_blank_png(input_dir / f"inv_{i:03d}.png")

    # 4장 중 2장(50%)를 invalid biznum으로 모킹.
    _mock_invoice(
        monkeypatch,
        invalid_biznum_filenames=("inv_000.png", "inv_001.png"),
    )

    warnings_captured: list[str] = []

    class _WarnSpy:
        def info(self, msg: str) -> None:
            pass

        def success(self, msg: str) -> None:
            pass

        def warning(self, msg: str) -> None:
            warnings_captured.append(msg)

        def error(self, msg: str) -> None:
            pass

    monkeypatch.setattr(scenario, "demo_logger", lambda case_id: _WarnSpy())

    out_dir = tmp_path / "out"
    summary = scenario.run(input_dir=input_dir, output_dir=out_dir)

    assert summary["processed"] == 4
    assert summary["failed"] == 2
    assert summary["failure_rate"] == 0.5
    assert summary["quality_warning"] is True
    # prominent warning이 demo_logger.warning을 통해 출력됐는지 확인.
    assert any("품질 경고" in w for w in warnings_captured)
    assert any("DEMO_SAFE" in w for w in warnings_captured)


def test_scenario_no_warning_below_threshold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """실패율이 50% 미만이면 quality_warning=False (기본 시드 ~7% 실패에 해당)."""
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    for i in range(10):
        _make_blank_png(input_dir / f"inv_{i:03d}.png")

    # 10장 중 1장만 실패 (10%) — threshold 미만.
    _mock_invoice(monkeypatch, fail_filenames=("inv_005.png",))

    out_dir = tmp_path / "out"
    summary = scenario.run(input_dir=input_dir, output_dir=out_dir)

    assert summary["processed"] == 10
    assert summary["failed"] == 1
    assert summary["failure_rate"] == 0.1
    assert summary["quality_warning"] is False


def test_scenario_no_warning_when_zero_processed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """processed=0 (빈 디렉토리)일 때 quality_warning=False, failure_rate=0.0."""
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    empty_seed = tmp_path / "empty"
    empty_seed.mkdir()
    monkeypatch.setattr(scenario, "_DEFAULT_FALLBACK_DIR", empty_seed)

    _mock_invoice(monkeypatch)
    out_dir = tmp_path / "out"
    summary = scenario.run(input_dir=input_dir, output_dir=out_dir)
    assert summary["processed"] == 0
    assert summary["failure_rate"] == 0.0
    assert summary["quality_warning"] is False


def test_scenario_csv_has_standard_columns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    _make_blank_png(input_dir / "inv_001.png")

    _mock_invoice(monkeypatch)
    out_dir = tmp_path / "out"
    scenario.run(input_dir=input_dir, output_dir=out_dir)

    utf8_text = (out_dir / "invoices_utf8.csv").read_text(encoding="utf-8-sig")
    header = utf8_text.splitlines()[0]
    expected = [
        "거래일",
        "거래번호",
        "공급자번호",
        "공급자명",
        "공급받는자번호",
        "공급받는자명",
        "공급가액",
        "부가세",
        "합계",
    ]
    for col in expected:
        assert col in header
