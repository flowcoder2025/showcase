"""영수증 OCR — Gemma 4 E2B 기반.

NOTE: 외부 호출은 모듈 참조로 호출:
    from core.ocr import receipt
    receipt.extract(...)

receipt 자체는 외부 호출이 아님 — ``gemma.extract``를 호출하는 wrapper.
INTERCEPT_TARGETS 등록 불필요 (safe_mode가 gemma 단독으로 patch).

Architecture
- ReceiptData TypedDict: merchant / amount / date / items / raw_text 5-field 계약.
- RECEIPT_SCHEMA: gemma.extract 내부 jsonschema 검증 + 1회 retry 자동 활용.
- _normalize: gemma 응답을 ReceiptData로 정규화. safe_dummy / parse_error /
  missing field 3가지 실패 채널을 명시적으로 분기한다.
- _parse_amount: ₩, 콤마, "원" suffix, 소수점, 음수(환불 영수증) 처리.
- _normalize_date: ISO/슬래시/점/한국어 등 9개 포맷 → YYYY-MM-DD.

음수 amount 허용 — 환불 영수증 시연 시 필요 (정직성 명시).
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, TypedDict

from core.ocr import gemma


class ReceiptData(TypedDict):
    """정규화된 영수증 구조.

    Fields:
        merchant: 가게/사업자명.
        amount: 총액 (원). 환불 영수증은 음수 가능.
        date: ``YYYY-MM-DD`` 정규화 날짜.
        items: 품목 목록 (선택적, 비어 있으면 ``[]``).
        raw_text: OCR 원본 텍스트 — 디버깅/감사용.
    """

    merchant: str
    amount: int
    date: str
    items: list[dict[str, Any]]
    raw_text: str


RECEIPT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "merchant": {"type": "string"},
        # OCR이 string/숫자 어느 쪽이든 줄 수 있어 유니온 허용.
        "amount": {"type": ["integer", "string", "number"]},
        "date": {"type": "string"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "qty": {"type": ["integer", "string", "number"]},
                    "price": {"type": ["integer", "string", "number"]},
                },
            },
        },
        "raw_text": {"type": "string"},
    },
    "required": ["merchant", "amount", "date"],
}


# -- public API -------------------------------------------------------------


def extract(image_path: Path | str) -> ReceiptData:
    """영수증 이미지 → ReceiptData.

    Args:
        image_path: OCR 대상 이미지 경로.

    Returns:
        정규화된 ``ReceiptData``. safe_mode 시 placeholder, 정상 응답 시 정규화 필드.

    Raises:
        ValueError: gemma 응답이 parse error거나 필수 필드(merchant/amount/date)가
            누락된 경우. 메시지에 raw_text 또는 missing 필드명 포함.
    """
    raw = gemma.extract(image_path, model="gemma4:e2b", schema=RECEIPT_SCHEMA)
    return _normalize(raw, image_path)


# -- internal helpers -------------------------------------------------------


def _normalize(raw: dict[str, Any], image_path: Path | str) -> ReceiptData:
    """gemma.extract 결과를 ReceiptData로 정규화.

    실패 채널:
        - ``{"_safe": True, ...}`` → placeholder ReceiptData (시연 흐름 보호).
        - ``{"_raw_text": ..., "_parse_error": ...}`` → ``ValueError`` (raw_text 포함).
        - 필수 필드 누락 → ``ValueError`` (missing 필드명 포함).
    """
    if raw.get("_safe"):
        return ReceiptData(
            merchant="[SAFE-FALLBACK]",
            amount=0,
            date="2026-01-01",
            items=[],
            raw_text=f"safe_dummy: {raw.get('image_hash', '')}",
        )

    if "_parse_error" in raw:
        raise ValueError(
            f"OCR response could not be parsed: {raw.get('_parse_error')}; "
            f"raw_text={raw.get('_raw_text', '')!r}"
        )

    missing = [k for k in ("merchant", "amount", "date") if k not in raw]
    if missing:
        raise ValueError(f"OCR response missing required fields {missing}; raw={raw!r}")

    return ReceiptData(
        merchant=str(raw["merchant"]).strip(),
        amount=_parse_amount(raw["amount"]),
        date=_normalize_date(raw["date"]),
        items=list(raw.get("items", [])),
        raw_text=str(raw.get("raw_text", "")),
    )


def _parse_amount(value: Any) -> int:
    """숫자/문자열 → 정수 amount.

    처리:
        - ``int`` 그대로.
        - ``float`` truncate.
        - 통화 기호(``₩``), 콤마, ``원`` suffix, whitespace 제거.
        - 소수점은 정수부만 사용 (``"1500.50"`` → 1500).
        - 음수 허용 (환불 영수증).

    Raises:
        ValueError: 숫자로 변환 불가능한 입력.
    """
    if isinstance(value, bool):  # bool은 int 서브클래스 — 명시적으로 차단
        raise ValueError(f"cannot parse amount: {value!r}")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    s = str(value).strip()
    s = re.sub(r"[₩,원\s]", "", s)
    if "." in s:
        s = s.split(".")[0]
    if not s or s == "-":
        raise ValueError(f"cannot parse amount: {value!r}")
    try:
        return int(s)
    except ValueError as e:
        raise ValueError(f"cannot parse amount: {value!r}") from e


_DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y.%m.%d",
    "%Y년 %m월 %d일",
    "%Y년%m월%d일",
    "%y-%m-%d",
    "%y/%m/%d",
    "%m/%d/%Y",
    "%d/%m/%Y",
)


def _normalize_date(value: str) -> str:
    """다양한 날짜 입력 → ``YYYY-MM-DD``.

    지원 포맷 (순서대로 시도):
        ``2026-05-01``, ``2026/05/01``, ``2026.05.01``, ``2026년 5월 1일``,
        ``2026년5월1일``, ``26-05-01`` (2자리 연도 — Python이 50 미만은 2000년대,
        50 이상은 1900년대로 해석), ``26/05/01``, ``05/01/2026``, ``01/05/2026``.

    Raises:
        ValueError: 어떤 포맷에도 매칭되지 않는 입력.
    """
    s = str(value).strip()
    s = s.replace("  ", " ")
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"cannot parse date: {value!r}")
