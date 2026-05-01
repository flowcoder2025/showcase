"""T10: core.ocr.receipt — 영수증 OCR contract & normalization 검증.

대부분 ``gemma.extract`` mock 기반. 실제 Ollama 호출 없음.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from core.ocr import gemma, receipt

# -- extract: contract via gemma.extract mock -------------------------------


def _mock_gemma(monkeypatch: pytest.MonkeyPatch, payload: dict[str, Any]) -> list[dict[str, Any]]:
    """``gemma.extract`` mock + 호출 인자 캡처."""
    calls: list[dict[str, Any]] = []

    def _fake(image_path: Path | str, **kwargs: Any) -> dict[str, Any]:
        calls.append({"image_path": image_path, **kwargs})
        return payload

    monkeypatch.setattr(gemma, "extract", _fake)
    return calls


def test_extract_returns_typed_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_gemma(
        monkeypatch,
        {
            "merchant": "AX마트",
            "amount": 15000,
            "date": "2026-05-01",
            "items": [{"name": "사과", "qty": 1, "price": 15000}],
            "raw_text": "AX마트 15000원",
        },
    )
    result = receipt.extract("/tmp/r.png")
    assert result["merchant"] == "AX마트"
    assert result["amount"] == 15000
    assert result["date"] == "2026-05-01"
    assert result["items"] == [{"name": "사과", "qty": 1, "price": 15000}]
    assert result["raw_text"] == "AX마트 15000원"


def test_extract_safe_fallback_returns_placeholder(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_gemma(monkeypatch, {"_safe": True, "image_hash": "abc12345"})
    result = receipt.extract("/tmp/r.png")
    assert result["merchant"] == "[SAFE-FALLBACK]"
    assert result["amount"] == 0
    assert result["date"] == "2026-01-01"
    assert result["items"] == []
    assert "abc12345" in result["raw_text"]


def test_extract_parse_error_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_gemma(
        monkeypatch,
        {"_raw_text": "garbage text from OCR", "_parse_error": "JSON decode failed"},
    )
    with pytest.raises(ValueError) as exc_info:
        receipt.extract("/tmp/r.png")
    msg = str(exc_info.value)
    assert "garbage text from OCR" in msg
    assert "JSON decode failed" in msg


def test_extract_missing_required_field_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_gemma(monkeypatch, {"merchant": "X"})
    with pytest.raises(ValueError) as exc_info:
        receipt.extract("/tmp/r.png")
    msg = str(exc_info.value)
    assert "amount" in msg
    assert "date" in msg


# -- _parse_amount ----------------------------------------------------------


def test_parse_amount_integer() -> None:
    assert receipt._parse_amount(15000) == 15000


def test_parse_amount_with_currency_symbol() -> None:
    assert receipt._parse_amount("₩15,000") == 15000


def test_parse_amount_with_korean_won_suffix() -> None:
    assert receipt._parse_amount("15,000원") == 15000


def test_parse_amount_with_decimal() -> None:
    assert receipt._parse_amount("1500.50") == 1500


def test_parse_amount_negative_for_refund() -> None:
    assert receipt._parse_amount("-15000") == -15000


def test_parse_amount_invalid_raises() -> None:
    with pytest.raises(ValueError):
        receipt._parse_amount("not-a-number")


def test_parse_amount_empty_raises() -> None:
    with pytest.raises(ValueError):
        receipt._parse_amount("")


# -- _normalize_date --------------------------------------------------------


def test_normalize_date_iso() -> None:
    assert receipt._normalize_date("2026-05-01") == "2026-05-01"


def test_normalize_date_slash() -> None:
    assert receipt._normalize_date("2026/05/01") == "2026-05-01"


def test_normalize_date_dot() -> None:
    assert receipt._normalize_date("2026.05.01") == "2026-05-01"


def test_normalize_date_korean() -> None:
    assert receipt._normalize_date("2026년 5월 1일") == "2026-05-01"


def test_normalize_date_korean_no_space() -> None:
    assert receipt._normalize_date("2026년5월1일") == "2026-05-01"


def test_normalize_date_two_digit_year() -> None:
    assert receipt._normalize_date("26-05-01") == "2026-05-01"


def test_normalize_date_invalid_raises() -> None:
    with pytest.raises(ValueError):
        receipt._normalize_date("not-a-date")


# -- extract: normalization passthrough -------------------------------------


def test_extract_normalizes_date_format(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_gemma(
        monkeypatch,
        {"merchant": "AX마트", "amount": 1000, "date": "2026/05/01"},
    )
    result = receipt.extract("/tmp/r.png")
    assert result["date"] == "2026-05-01"


def test_extract_normalizes_amount_with_won(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_gemma(
        monkeypatch,
        {"merchant": "AX마트", "amount": "15,000원", "date": "2026-05-01"},
    )
    result = receipt.extract("/tmp/r.png")
    assert result["amount"] == 15000


def test_extract_items_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    items = [
        {"name": "사과", "qty": 1, "price": 5000},
        {"name": "배", "qty": 2, "price": 10000},
    ]
    _mock_gemma(
        monkeypatch,
        {"merchant": "M", "amount": 15000, "date": "2026-05-01", "items": items},
    )
    result = receipt.extract("/tmp/r.png")
    assert result["items"] == items


def test_extract_items_default_empty_list(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_gemma(
        monkeypatch,
        {"merchant": "M", "amount": 1000, "date": "2026-05-01"},
    )
    result = receipt.extract("/tmp/r.png")
    assert result["items"] == []


def test_extract_raw_text_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_gemma(
        monkeypatch,
        {
            "merchant": "M",
            "amount": 1000,
            "date": "2026-05-01",
            "raw_text": "가게명 1500원",
        },
    )
    result = receipt.extract("/tmp/r.png")
    assert result["raw_text"] == "가게명 1500원"


def test_extract_uses_e2b_model(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _mock_gemma(
        monkeypatch,
        {"merchant": "M", "amount": 1000, "date": "2026-05-01"},
    )
    receipt.extract("/tmp/r.png")
    assert calls[0]["model"] == "gemma4:e2b"


def test_extract_passes_receipt_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _mock_gemma(
        monkeypatch,
        {"merchant": "M", "amount": 1000, "date": "2026-05-01"},
    )
    receipt.extract("/tmp/r.png")
    assert calls[0]["schema"] is receipt.RECEIPT_SCHEMA
