"""T11: case07 — 영수증 일괄 OCR → 경비 정리 엑셀.

``core.ocr.receipt.extract`` mock 기반 contract 검증. 실제 Ollama 호출 없음.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import openpyxl
import pytest
from PIL import Image

from cases.case07_ocr_receipt_to_excel import scenario
from core.ocr import receipt
from core.ocr.receipt import ReceiptData

# -- helpers ---------------------------------------------------------------


def _make_blank_png(path: Path) -> None:
    """1x1 흰색 PNG — input 디렉토리 채움 용도."""
    Image.new("RGB", (10, 10), "white").save(path)


def _mock_receipt(
    monkeypatch: pytest.MonkeyPatch,
    response: ReceiptData | None = None,
    fail_filenames: tuple[str, ...] = (),
) -> list[Path]:
    """``receipt.extract`` mock — ``fail_filenames``는 ValueError raise."""
    calls: list[Path] = []
    default: ReceiptData = response or ReceiptData(
        merchant="스타벅스 강남점",
        amount=5500,
        date="2026-04-15",
        items=[{"name": "아메리카노", "qty": 1, "price": 5500}],
        raw_text="스타벅스 5500",
    )

    def _fake(image_path: Path | str) -> ReceiptData:
        p = Path(image_path)
        calls.append(p)
        if p.name in fail_filenames:
            raise ValueError(f"mock OCR failure for {p.name}")
        return default

    monkeypatch.setattr(receipt, "extract", _fake)
    return calls


# -- 1. 기본 처리 ----------------------------------------------------------


def test_run_processes_all_images_in_input_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    for i in range(5):
        _make_blank_png(input_dir / f"r{i:03d}.png")

    _mock_receipt(monkeypatch)
    output_path = tmp_path / "out" / "expense.xlsx"

    summary = scenario.run(input_dir=input_dir, output_path=output_path)

    assert summary["processed"] == 5
    assert summary["errors"] == 0
    assert output_path.exists()

    wb = openpyxl.load_workbook(output_path)
    ws = wb.active
    assert ws is not None
    # 헤더 1행 + 데이터 5행 = 총 6행
    assert ws.max_row == 6


# -- 2. personas fallback --------------------------------------------------


def test_run_uses_personas_fallback_when_input_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """case input/ 디렉토리가 비어 있으면 personas/sample_data/receipts/ 사용."""
    # personas 디렉토리에 시드가 없어도 동작하도록 fallback 위치를 monkeypatch
    seed_dir = tmp_path / "seeds"
    seed_dir.mkdir()
    for i in range(3):
        _make_blank_png(seed_dir / f"r{i:03d}.png")
    # 정답 파일도 추가 — _underscore prefix 스킵 검증 겸함
    (seed_dir / "_ground_truth.json").write_text("[]", encoding="utf-8")

    # case 디렉토리의 input은 빈 디렉토리로 두고 fallback 경로를 monkeypatch
    monkeypatch.setattr(scenario, "_DEFAULT_FALLBACK_DIR", seed_dir)
    _mock_receipt(monkeypatch)

    output_path = tmp_path / "out" / "expense.xlsx"
    # input_dir=None → 기본값 (case_dir/input → 비어있음 → fallback)
    summary = scenario.run(input_dir=None, output_path=output_path)

    assert summary["processed"] == 3
    assert summary["errors"] == 0


# -- 3. per-image 실패 격리 -------------------------------------------------


def test_run_continues_after_per_image_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    for i in range(4):
        _make_blank_png(input_dir / f"r{i:03d}.png")

    _mock_receipt(monkeypatch, fail_filenames=("r001.png", "r003.png"))
    output_path = tmp_path / "out" / "expense.xlsx"

    summary = scenario.run(input_dir=input_dir, output_path=output_path)

    assert summary["processed"] == 2
    assert summary["errors"] == 2

    wb = openpyxl.load_workbook(output_path)
    ws = wb.active
    assert ws is not None
    # 헤더 + 성공 2건 = 3행
    assert ws.max_row == 3


# -- 4. safe-fallback 데이터 ------------------------------------------------


def test_run_safe_mode_returns_safe_fallback_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    for i in range(4):
        _make_blank_png(input_dir / f"r{i:03d}.png")

    safe_data: ReceiptData = ReceiptData(
        merchant="[SAFE-FALLBACK]",
        amount=0,
        date="2026-01-01",
        items=[],
        raw_text="safe_dummy: abc123",
    )
    _mock_receipt(monkeypatch, response=safe_data)
    output_path = tmp_path / "out" / "expense.xlsx"

    summary = scenario.run(input_dir=input_dir, output_path=output_path)

    assert summary["processed"] == 4
    assert summary["errors"] == 0

    wb = openpyxl.load_workbook(output_path)
    ws = wb.active
    assert ws is not None
    merchants = [ws.cell(row=r, column=2).value for r in range(2, 6)]
    assert all(m == "[SAFE-FALLBACK]" for m in merchants)


# -- 5. underscore prefix 스킵 ----------------------------------------------


def test_run_skips_underscore_prefix_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    _make_blank_png(input_dir / "r001.png")
    _make_blank_png(input_dir / "r002.png")
    _make_blank_png(input_dir / "_temp.png")  # underscore → 스킵
    (input_dir / "_ground_truth.json").write_text("[]", encoding="utf-8")  # 스킵

    _mock_receipt(monkeypatch)
    output_path = tmp_path / "out" / "expense.xlsx"

    summary = scenario.run(input_dir=input_dir, output_path=output_path)

    assert summary["processed"] == 2
    assert summary["errors"] == 0


# -- 6. xlsx 컬럼 헤더 ------------------------------------------------------


def test_run_output_xlsx_columns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    _make_blank_png(input_dir / "r001.png")

    _mock_receipt(monkeypatch)
    output_path = tmp_path / "out" / "expense.xlsx"
    scenario.run(input_dir=input_dir, output_path=output_path)

    wb = openpyxl.load_workbook(output_path)
    ws = wb.active
    assert ws is not None
    headers = [ws.cell(row=1, column=c).value for c in range(1, 6)]
    assert headers == ["거래일", "가맹점", "카테고리", "결제수단", "금액"]


# -- 7. 카테고리 매핑 ------------------------------------------------------


def test_guess_category_known_prefixes() -> None:
    assert scenario._guess_category("스타벅스 강남점") == "커피"
    assert scenario._guess_category("이디야 역삼") == "커피"
    assert scenario._guess_category("롯데마트 송파") == "장보기"
    assert scenario._guess_category("이마트 트레이더스") == "장보기"
    assert scenario._guess_category("GS25 서초") == "편의점"
    assert scenario._guess_category("CU 청담") == "편의점"
    assert scenario._guess_category("세븐일레븐 합정") == "편의점"
    assert scenario._guess_category("맥도날드 강남대로") == "식사"
    assert scenario._guess_category("알 수 없는 가게") == "기타"


# -- 8. 빈 디렉토리 ---------------------------------------------------------


def test_run_zero_images(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()

    # personas fallback도 빈 디렉토리로
    empty_seed = tmp_path / "empty_seed"
    empty_seed.mkdir()
    monkeypatch.setattr(scenario, "_DEFAULT_FALLBACK_DIR", empty_seed)

    _mock_receipt(monkeypatch)
    output_path = tmp_path / "out" / "expense.xlsx"

    summary = scenario.run(input_dir=input_dir, output_path=output_path)

    assert summary["processed"] == 0
    assert summary["errors"] == 0
    # xlsx은 헤더만 있어야 함
    wb = openpyxl.load_workbook(output_path)
    ws = wb.active
    assert ws is not None
    assert ws.max_row == 1


# -- 9. 이미지 확장자 필터 -------------------------------------------------


def test_run_filters_only_image_extensions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    _make_blank_png(input_dir / "r001.png")
    _make_blank_png(input_dir / "r002.jpg")
    _make_blank_png(input_dir / "r003.jpeg")
    (input_dir / "notes.txt").write_text("ignore me", encoding="utf-8")
    (input_dir / "doc.pdf").write_bytes(b"%PDF-1.4 fake")

    _mock_receipt(monkeypatch)
    output_path = tmp_path / "out" / "expense.xlsx"
    summary = scenario.run(input_dir=input_dir, output_path=output_path)

    assert summary["processed"] == 3
    assert summary["errors"] == 0


# -- 10. output 디렉토리 자동 생성 -----------------------------------------


def test_run_creates_output_dir_if_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    _make_blank_png(input_dir / "r001.png")

    _mock_receipt(monkeypatch)
    output_path = tmp_path / "deep" / "nested" / "out" / "expense.xlsx"
    assert not output_path.parent.exists()

    scenario.run(input_dir=input_dir, output_path=output_path)
    assert output_path.exists()


# -- 11. summary["rows"] 구조 -----------------------------------------------


def test_run_summary_rows_structure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    _make_blank_png(input_dir / "r001.png")
    _make_blank_png(input_dir / "r002.png")

    _mock_receipt(monkeypatch)
    output_path = tmp_path / "out" / "expense.xlsx"
    summary = scenario.run(input_dir=input_dir, output_path=output_path)

    rows: list[dict[str, Any]] = summary["rows"]
    assert len(rows) == 2
    for row in rows:
        assert "filename" in row
        assert "merchant" in row
        assert "amount" in row


# -- 12. 금액은 정수 ---------------------------------------------------------


def test_run_xlsx_amount_is_integer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    _make_blank_png(input_dir / "r001.png")

    _mock_receipt(monkeypatch)
    output_path = tmp_path / "out" / "expense.xlsx"
    scenario.run(input_dir=input_dir, output_path=output_path)

    wb = openpyxl.load_workbook(output_path)
    ws = wb.active
    assert ws is not None
    amount_cell = ws.cell(row=2, column=5).value
    assert isinstance(amount_cell, int), f"expected int, got {type(amount_cell).__name__}"
    assert amount_cell == 5500
