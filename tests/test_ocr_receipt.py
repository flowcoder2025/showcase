"""T10: core.ocr.receipt — 영수증 OCR contract & normalization 검증.

대부분 ``gemma.extract`` mock 기반. 실제 Ollama 호출 없음.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from flowcoder_office_tools.ocr import gemma, receipt

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


def test_normalize_date_rejects_ambiguous_slash_format() -> None:
    """R2-H2 regression: ``MM/DD/YYYY`` 와 ``DD/MM/YYYY`` 는 silent misparse
    위험으로 둘 다 거절한다 (``05/06/2026`` → 미국식인지 유럽식인지 불명)."""
    with pytest.raises(ValueError):
        receipt._normalize_date("05/06/2026")
    with pytest.raises(ValueError):
        receipt._normalize_date("12/31/2025")
    with pytest.raises(ValueError):
        receipt._normalize_date("31/12/2025")


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


# -- T10.5: items qty/price normalization ----------------------------------


def test_normalize_items_string_qty_price(monkeypatch: pytest.MonkeyPatch) -> None:
    """items의 qty/price string → int 변환 (₩, 콤마, 원 제거)."""
    _mock_gemma(
        monkeypatch,
        {
            "merchant": "M",
            "amount": 15000,
            "date": "2026-05-01",
            "items": [{"name": "사과", "qty": "3", "price": "₩15,000"}],
        },
    )
    result = receipt.extract("/tmp/r.png")
    assert result["items"] == [{"name": "사과", "qty": 3, "price": 15000}]


def test_normalize_items_invalid_qty_fallback_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """변환 불가능한 qty/price → 0 (silent fallback)."""
    _mock_gemma(
        monkeypatch,
        {
            "merchant": "M",
            "amount": 15000,
            "date": "2026-05-01",
            "items": [{"name": "X", "qty": "abc", "price": "xyz"}],
        },
    )
    result = receipt.extract("/tmp/r.png")
    assert result["items"] == [{"name": "X", "qty": 0, "price": 0}]


def test_normalize_items_strips_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """item name의 surrounding whitespace 제거."""
    _mock_gemma(
        monkeypatch,
        {
            "merchant": "M",
            "amount": 4500,
            "date": "2026-05-01",
            "items": [{"name": "  카페라떼  ", "qty": 1, "price": 4500}],
        },
    )
    result = receipt.extract("/tmp/r.png")
    assert result["items"][0]["name"] == "카페라떼"


def test_normalize_items_skips_non_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    """items에 dict가 아닌 항목 (string 등) 포함 → 결과에서 제외."""
    _mock_gemma(
        monkeypatch,
        {
            "merchant": "M",
            "amount": 5000,
            "date": "2026-05-01",
            "items": [{"name": "정상", "qty": 1, "price": 5000}, "garbage", 42],
        },
    )
    result = receipt.extract("/tmp/r.png")
    assert result["items"] == [{"name": "정상", "qty": 1, "price": 5000}]


def test_normalize_items_partial_fields_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    """qty만 있고 price 없는 item → qty 정규화, price 키는 결과에 없음."""
    _mock_gemma(
        monkeypatch,
        {
            "merchant": "M",
            "amount": 1000,
            "date": "2026-05-01",
            "items": [{"name": "메모", "qty": "5"}],
        },
    )
    result = receipt.extract("/tmp/r.png")
    assert result["items"] == [{"name": "메모", "qty": 5}]


# -- T10.5: amount sanity warning ------------------------------------------


class _RecordingLogger:
    """warning 호출 인자를 캡처하는 minimal logger stub."""

    def __init__(self) -> None:
        self.warnings: list[str] = []

    def info(self, msg: str) -> None:  # pragma: no cover - unused
        pass

    def success(self, msg: str) -> None:  # pragma: no cover - unused
        pass

    def warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def error(self, msg: str) -> None:  # pragma: no cover - unused
        pass


def _patch_demo_logger(monkeypatch: pytest.MonkeyPatch) -> _RecordingLogger:
    """receipt 모듈이 사용하는 demo_logger.demo_logger를 RecordingLogger로 교체."""
    from flowcoder_office_tools.common import demo_logger as dl_module

    rec = _RecordingLogger()
    monkeypatch.setattr(dl_module, "demo_logger", lambda _case_id: rec)
    return rec


def test_extract_warns_on_zero_amount(monkeypatch: pytest.MonkeyPatch) -> None:
    """amount=0 → demo_logger.warning 호출되며 ReceiptData는 정상 반환."""
    _mock_gemma(
        monkeypatch,
        {"merchant": "M", "amount": 0, "date": "2026-05-01"},
    )
    rec = _patch_demo_logger(monkeypatch)
    result = receipt.extract("/tmp/r.png")
    assert result["amount"] == 0
    assert len(rec.warnings) == 1
    assert "suspicious amount" in rec.warnings[0]


def test_extract_warns_on_huge_amount(monkeypatch: pytest.MonkeyPatch) -> None:
    """amount > 100억 → warning + 정상 반환."""
    _mock_gemma(
        monkeypatch,
        {"merchant": "M", "amount": 11_000_000_000, "date": "2026-05-01"},
    )
    rec = _patch_demo_logger(monkeypatch)
    result = receipt.extract("/tmp/r.png")
    assert result["amount"] == 11_000_000_000
    assert len(rec.warnings) == 1
    assert "11,000,000,000" in rec.warnings[0]


def test_extract_no_warn_on_normal_amount(monkeypatch: pytest.MonkeyPatch) -> None:
    """정상 범위 amount → warning 미호출."""
    _mock_gemma(
        monkeypatch,
        {"merchant": "M", "amount": 15000, "date": "2026-05-01"},
    )
    rec = _patch_demo_logger(monkeypatch)
    receipt.extract("/tmp/r.png")
    assert rec.warnings == []


def test_extract_warns_on_negative_huge_amount(monkeypatch: pytest.MonkeyPatch) -> None:
    """abs(amount) > 100억 (음수 환불) → warning."""
    _mock_gemma(
        monkeypatch,
        {"merchant": "M", "amount": -11_000_000_000, "date": "2026-05-01"},
    )
    rec = _patch_demo_logger(monkeypatch)
    result = receipt.extract("/tmp/r.png")
    assert result["amount"] == -11_000_000_000
    assert len(rec.warnings) == 1


# -- T11.5: merchant trim ---------------------------------------------------


def test_normalize_merchant_strips_newline(monkeypatch: pytest.MonkeyPatch) -> None:
    """merchant에 trailing newline → 제거."""
    _mock_gemma(
        monkeypatch,
        {"merchant": "스타벅스 강남점\n", "amount": 5500, "date": "2026-05-01"},
    )
    result = receipt.extract("/tmp/r.png")
    assert result["merchant"] == "스타벅스 강남점"


def test_normalize_merchant_collapses_multispace(monkeypatch: pytest.MonkeyPatch) -> None:
    """multi-space → single space로 축약."""
    _mock_gemma(
        monkeypatch,
        {"merchant": "스타벅스   강남점", "amount": 5500, "date": "2026-05-01"},
    )
    result = receipt.extract("/tmp/r.png")
    assert result["merchant"] == "스타벅스 강남점"


def test_normalize_merchant_zero_width_chars(monkeypatch: pytest.MonkeyPatch) -> None:
    """zero-width 공백 문자(ZWSP/ZWNJ/ZWJ) 제거."""
    _mock_gemma(
        monkeypatch,
        # U+200B (ZWSP) 삽입
        {"merchant": "스타벅스​ 강남", "amount": 5500, "date": "2026-05-01"},
    )
    result = receipt.extract("/tmp/r.png")
    assert result["merchant"] == "스타벅스 강남"


def test_normalize_merchant_strips_tab_and_cr(monkeypatch: pytest.MonkeyPatch) -> None:
    """탭/캐리지리턴 → space로 변환 후 collapse."""
    _mock_gemma(
        monkeypatch,
        {"merchant": "이디야\t역삼\r점", "amount": 4500, "date": "2026-05-01"},
    )
    result = receipt.extract("/tmp/r.png")
    assert result["merchant"] == "이디야 역삼 점"
