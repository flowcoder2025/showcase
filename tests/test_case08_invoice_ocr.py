"""T15: case08 — 세금계산서 일괄 OCR → 회계 CSV (T38 ScenarioResult)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from flowcoder_office_tools.ocr import invoice
from flowcoder_office_tools.ocr.invoice import InvoiceData
from PIL import Image

from cases.case08_ocr_invoice_to_csv import scenario

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
    calls: list[Path] = []
    default = response or _make_invoice_data()

    def _fake(image_path: Path | str) -> InvoiceData:
        p = Path(image_path)
        calls.append(p)
        if p.name in fail_filenames:
            raise ValueError(f"mock OCR failure for {p.name}")
        if p.name in invalid_biznum_filenames:
            return _make_invoice_data(supplier_biznum="123-45-67890")
        return default

    monkeypatch.setattr(invoice, "extract", _fake)
    return calls


def _output_paths(result: dict, out_dir: Path) -> tuple[Path, Path, Path]:
    """case08 output_files 순서: utf8 csv / cp949 csv / failures json."""
    files = result["output_files"]
    assert len(files) == 3
    return files[0], files[1], files[2]


# -- 1. deterministic safe mode --------------------------------------------


def test_scenario_runs_safe_mode_returns_deterministic_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    for i in range(3):
        _make_blank_png(input_dir / f"inv_{i:03d}.png")

    _mock_invoice(monkeypatch)
    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"

    r1 = scenario.run(input_dir=input_dir, output_dir=out1)
    r2 = scenario.run(input_dir=input_dir, output_dir=out2)

    assert r1["metrics"]["processed"] == r2["metrics"]["processed"] == 3
    assert r1["metrics"]["verified"] == r2["metrics"]["verified"] == 3
    assert r1["metrics"]["failed"] == r2["metrics"]["failed"] == 0
    assert r1["failures"] == r2["failures"] == []

    assert (out1 / "invoices_utf8.csv").read_bytes() == (out2 / "invoices_utf8.csv").read_bytes()
    assert (out1 / "invoices_cp949.csv").read_bytes() == (out2 / "invoices_cp949.csv").read_bytes()


# -- 2. dual CSV outputs ----------------------------------------------------


def test_scenario_creates_both_csv_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    _make_blank_png(input_dir / "inv_001.png")

    _mock_invoice(monkeypatch)
    out_dir = tmp_path / "out"
    result = scenario.run(input_dir=input_dir, output_dir=out_dir)

    utf8_path, cp949_path, failures_path = _output_paths(result, out_dir)
    assert utf8_path.exists()
    assert cp949_path.exists()
    assert failures_path.name == "validation_failures.json"

    with utf8_path.open("rb") as f:
        assert f.read(3) == b"\xef\xbb\xbf"
    with cp949_path.open("rb") as f:
        assert f.read(3) != b"\xef\xbb\xbf"
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

    _mock_invoice(
        monkeypatch,
        fail_filenames=("inv_001.png",),
        invalid_biznum_filenames=("inv_003.png",),
    )

    out_dir = tmp_path / "out"
    result = scenario.run(input_dir=input_dir, output_dir=out_dir)

    assert result["metrics"]["processed"] == 5
    assert result["metrics"]["verified"] == 3
    assert result["metrics"]["failed"] == 2

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
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    _make_blank_png(input_dir / "inv_001.png")
    _mock_invoice(monkeypatch)

    out_dir = tmp_path / "out"
    result = scenario.run(input_dir=input_dir, output_dir=out_dir)

    failures_path = out_dir / "validation_failures.json"
    assert failures_path.exists()
    assert json.loads(failures_path.read_text(encoding="utf-8")) == []
    assert result["metrics"]["failed"] == 0


# -- 4. processes all seeds (real seeds on disk) ---------------------------


def test_scenario_processes_all_seeds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
    result = scenario.run(input_dir=seed_dir, output_dir=out_dir)

    assert result["metrics"]["processed"] == seed_count
    assert seed_count >= 30


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
    result = scenario.run(input_dir=input_dir, output_dir=out_dir)
    assert result["metrics"]["processed"] == 2


# -- 7. personas fallback ---------------------------------------------------


def test_scenario_uses_personas_fallback_when_input_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()
    for i in range(3):
        _make_blank_png(seed_dir / f"inv_{i:03d}.png")
    monkeypatch.setattr(scenario, "_DEFAULT_IN", seed_dir)

    _mock_invoice(monkeypatch)
    out_dir = tmp_path / "out"
    result = scenario.run(input_dir=None, output_dir=out_dir)

    assert result["metrics"]["processed"] == 3


# -- 8. 면세 거래 통과 ------------------------------------------------------


def test_scenario_accepts_tax_free_invoice(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    _make_blank_png(input_dir / "inv_001.png")

    tax_free = _make_invoice_data(total_supply=500_000, total_vat=0, total_amount=500_000)
    _mock_invoice(monkeypatch, response=tax_free)

    out_dir = tmp_path / "out"
    result = scenario.run(input_dir=input_dir, output_dir=out_dir)
    assert result["metrics"]["verified"] == 1
    assert result["metrics"]["failed"] == 0


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
    data = _make_invoice_data(total_supply=1_000_000, total_vat=99_000)
    reason = scenario._classify_failure(data)
    assert reason is not None
    assert "vat mismatch" in reason


def test_classify_failure_vat_within_tolerance() -> None:
    data = _make_invoice_data(total_supply=1005, total_vat=101, total_amount=1106)
    assert scenario._classify_failure(data) is None


def test_classify_failure_tax_free_passes() -> None:
    data = _make_invoice_data(total_supply=1_000_000, total_vat=0, total_amount=1_000_000)
    assert scenario._classify_failure(data) is None


# -- 10. per-image timer + summary 구조 ------------------------------------


def test_scenario_extras_per_image_ms(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    for i in range(4):
        _make_blank_png(input_dir / f"inv_{i:03d}.png")

    _mock_invoice(monkeypatch)
    out_dir = tmp_path / "out"
    result = scenario.run(input_dir=input_dir, output_dir=out_dir)

    per_image: list[dict[str, Any]] = result["extras"]["per_image_ms"]
    assert len(per_image) == 4
    for entry in per_image:
        assert "filename" in entry
        assert "elapsed_ms" in entry
        assert isinstance(entry["elapsed_ms"], float)
    assert "elapsed_seconds" in result["metrics"]
    assert isinstance(result["metrics"]["elapsed_seconds"], float)


# -- 11. 빈 디렉토리 --------------------------------------------------------


def test_scenario_zero_invoices(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    empty_seed = tmp_path / "empty"
    empty_seed.mkdir()
    monkeypatch.setattr(scenario, "_DEFAULT_IN", empty_seed)

    _mock_invoice(monkeypatch)
    out_dir = tmp_path / "out"
    result = scenario.run(input_dir=input_dir, output_dir=out_dir)
    assert result["metrics"]["processed"] == 0
    utf8_text = (out_dir / "invoices_utf8.csv").read_text(encoding="utf-8-sig")
    assert "거래일" in utf8_text
    assert utf8_text.count("\n") == 1


# -- 13. T15.5: 품질 경고 (failure_rate >= 50%) ----------------------------


def test_scenario_warns_on_high_failure_rate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    for i in range(4):
        _make_blank_png(input_dir / f"inv_{i:03d}.png")

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
    result = scenario.run(input_dir=input_dir, output_dir=out_dir)

    assert result["metrics"]["processed"] == 4
    assert result["metrics"]["failed"] == 2
    assert result["metrics"]["failure_rate"] == 0.5
    assert result["metrics"]["quality_warning"] is True
    assert any("품질 경고" in w for w in warnings_captured)
    assert any("DEMO_SAFE" in w for w in warnings_captured)


def test_scenario_no_warning_below_threshold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    for i in range(10):
        _make_blank_png(input_dir / f"inv_{i:03d}.png")

    _mock_invoice(monkeypatch, fail_filenames=("inv_005.png",))

    out_dir = tmp_path / "out"
    result = scenario.run(input_dir=input_dir, output_dir=out_dir)

    assert result["metrics"]["processed"] == 10
    assert result["metrics"]["failed"] == 1
    assert result["metrics"]["failure_rate"] == 0.1
    assert result["metrics"]["quality_warning"] is False


def test_scenario_no_warning_when_zero_processed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    empty_seed = tmp_path / "empty"
    empty_seed.mkdir()
    monkeypatch.setattr(scenario, "_DEFAULT_IN", empty_seed)

    _mock_invoice(monkeypatch)
    out_dir = tmp_path / "out"
    result = scenario.run(input_dir=input_dir, output_dir=out_dir)
    assert result["metrics"]["processed"] == 0
    assert result["metrics"]["failure_rate"] == 0.0
    assert result["metrics"]["quality_warning"] is False


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
