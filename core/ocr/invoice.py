"""세금계산서 OCR — Gemma 4 E4B + 회계 CSV export.

NOTE: 외부 호출은 모듈 참조로 호출:
    from core.ocr import invoice
    invoice.extract(...)

invoice 자체는 외부 호출이 아님 — ``gemma.extract``를 호출하는 wrapper.
INTERCEPT_TARGETS 등록 불필요 (safe_mode가 gemma 단독으로 patch).

Architecture
- InvoiceData TypedDict: 9-field 계약 (invoice_no/issue_date/supplier·buyer biznum+name/
  line_items/total_supply/total_vat/total_amount).
- INVOICE_SCHEMA: gemma.extract 내부 jsonschema 검증 + 1회 retry 자동 활용.
- validate_biznum: 한국 사업자등록번호 모듈러스 체크섬 (가중치 [1,3,7,1,3,7,1,3,5]).
- _validate_and_normalize: gemma 응답을 InvoiceData로 정규화.
  실패 채널: safe_dummy → placeholder, parse_error/missing field/biznum invalid/
  vat 불일치 → ValueError.
- to_accounting_csv: 회계SW 표준 CSV (utf-8 / cp949 선택).
  cp949 미지원 문자는 fail-fast (SI 호환성 우선) — UnicodeEncodeError raise.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Literal, TypedDict

from core.ocr import gemma


class InvoiceData(TypedDict):
    """정규화된 세금계산서 구조.

    Fields:
        invoice_no: 거래번호 (예: ``INV-2026-00042``).
        issue_date: 발행일 (``YYYY-MM-DD``).
        supplier_biznum: 공급자 사업자등록번호 (체크섬 검증 통과).
        supplier_name: 공급자 상호.
        buyer_biznum: 공급받는자 사업자등록번호 (체크섬 검증 통과).
        buyer_name: 공급받는자 상호.
        line_items: 품목 라인 (``name``/``qty``/``unit_price``/``amount``).
        total_supply: 공급가액 (원).
        total_vat: 부가세 (원). 면세 거래는 ``0``.
        total_amount: 합계 금액 (``total_supply + total_vat``).
    """

    invoice_no: str
    issue_date: str
    supplier_biznum: str
    supplier_name: str
    buyer_biznum: str
    buyer_name: str
    line_items: list[dict[str, Any]]
    total_supply: int
    total_vat: int
    total_amount: int


INVOICE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "invoice_no": {"type": "string"},
        "issue_date": {"type": "string"},
        "supplier_biznum": {"type": "string"},
        "supplier_name": {"type": "string"},
        "buyer_biznum": {"type": "string"},
        "buyer_name": {"type": "string"},
        "line_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "qty": {"type": ["integer", "string", "number"]},
                    "unit_price": {"type": ["integer", "string", "number"]},
                    "amount": {"type": ["integer", "string", "number"]},
                },
            },
        },
        # OCR이 string/숫자 어느 쪽이든 줄 수 있어 유니온 허용.
        "total_supply": {"type": ["integer", "string", "number"]},
        "total_vat": {"type": ["integer", "string", "number"]},
        "total_amount": {"type": ["integer", "string", "number"]},
    },
    "required": [
        "invoice_no",
        "issue_date",
        "supplier_biznum",
        "supplier_name",
        "buyer_biznum",
        "buyer_name",
        "total_supply",
        "total_vat",
        "total_amount",
    ],
}


_BIZNUM_WEIGHTS: tuple[int, ...] = (1, 3, 7, 1, 3, 7, 1, 3, 5)


# -- public API -------------------------------------------------------------


def validate_biznum(biznum: str) -> bool:
    """한국 사업자등록번호 10자리 모듈러스 체크섬.

    알고리즘 (국세청 공식):
        1. ``-`` 제거 후 10자리 숫자 검증.
        2. 가중치 [1,3,7,1,3,7,1,3,5] × 앞 9자리 합 = ``total``.
        3. ``total += (digit[8] * 5) // 10`` (8번째 자리 보정).
        4. ``check = (10 - (total % 10)) % 10``.
        5. ``check == digit[9]`` 이면 valid.

    Args:
        biznum: ``XXX-XX-XXXXX`` 또는 ``XXXXXXXXXX`` 형식.

    Returns:
        체크섬 통과 시 ``True``, 형식 또는 체크섬 실패 시 ``False``.
    """
    digits = biznum.replace("-", "")
    if len(digits) != 10 or not digits.isdigit():
        return False
    nums = [int(c) for c in digits]
    total = sum(d * w for d, w in zip(nums[:9], _BIZNUM_WEIGHTS, strict=True))
    total += (nums[8] * 5) // 10
    check = (10 - (total % 10)) % 10
    return check == nums[9]


def extract(image_path: Path | str) -> InvoiceData:
    """세금계산서 이미지 → InvoiceData.

    Args:
        image_path: OCR 대상 이미지 경로.

    Returns:
        정규화된 ``InvoiceData``. safe_mode 시 placeholder, 정상 응답 시 정규화 필드.

    Raises:
        ValueError: gemma 응답이 parse error거나 필수 필드 누락,
            biznum 체크섬 실패, 또는 vat 불일치 (면세 0 제외).
    """
    raw = gemma.extract(image_path, model="gemma4:e4b", schema=INVOICE_SCHEMA)
    return _validate_and_normalize(raw, image_path)


def to_accounting_csv(
    invoices: list[InvoiceData],
    out_path: Path | str,
    *,
    encoding: Literal["utf-8", "cp949"] = "utf-8",
) -> None:
    """회계SW (더존, 영림원 등) 표준 CSV로 export.

    Args:
        invoices: 정규화된 invoice 리스트.
        out_path: 저장 경로 (str/Path 모두 허용).
        encoding: ``utf-8`` (default) 또는 ``cp949`` (한국 회계SW 호환).

    Raises:
        UnicodeEncodeError: ``encoding="cp949"`` 인데 invoice 필드에 cp949 미지원
            문자(이모지 등)가 포함된 경우. SI 호환을 위해 ``errors="replace"``를
            쓰지 않고 fail-fast로 raise — 데이터 무결성 우선.

    NOTE: 컬럼 순서는 일반적 표준이지만 회계SW마다 다름. 향후 column_map override는
    case08 시나리오 또는 T15.5 fixer 단계에서 추가 가능.
    """
    out = Path(out_path)
    with out.open("w", encoding=encoding, newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
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
        )
        for inv in invoices:
            writer.writerow(
                [
                    inv["issue_date"],
                    inv["invoice_no"],
                    inv["supplier_biznum"],
                    inv["supplier_name"],
                    inv["buyer_biznum"],
                    inv["buyer_name"],
                    inv["total_supply"],
                    inv["total_vat"],
                    inv["total_amount"],
                ]
            )


# -- internal helpers -------------------------------------------------------


_REQUIRED_FIELDS: tuple[str, ...] = (
    "invoice_no",
    "issue_date",
    "supplier_biznum",
    "supplier_name",
    "buyer_biznum",
    "buyer_name",
    "total_supply",
    "total_vat",
    "total_amount",
)


def _validate_and_normalize(raw: dict[str, Any], image_path: Path | str) -> InvoiceData:
    """gemma.extract 결과를 InvoiceData로 정규화 + 검증.

    실패 채널:
        - ``{"_safe": True, ...}`` → placeholder InvoiceData (시연 흐름 보호).
        - ``{"_raw_text": ..., "_parse_error": ...}`` → ``ValueError``.
        - 필수 필드 누락 → ``ValueError`` (missing 필드명 포함).
        - biznum 체크섬 실패 → ``ValueError`` (supplier/buyer 명시).
        - ``total_vat != total_supply // 10`` 이며 면세(vat=0)도 아님 → ``ValueError``.
    """
    if raw.get("_safe"):
        image_hash = str(raw.get("image_hash", ""))
        return InvoiceData(
            invoice_no="[SAFE-FALLBACK]",
            issue_date="2026-01-01",
            supplier_biznum=_VALID_PLACEHOLDER_BIZNUM,
            supplier_name=f"[SAFE-FALLBACK:{image_hash}]",
            buyer_biznum=_VALID_PLACEHOLDER_BIZNUM,
            buyer_name=f"[SAFE-FALLBACK:{image_hash}]",
            line_items=[],
            total_supply=0,
            total_vat=0,
            total_amount=0,
        )

    if "_parse_error" in raw:
        raise ValueError(
            f"OCR response could not be parsed: {raw.get('_parse_error')}; "
            f"raw_text={raw.get('_raw_text', '')!r}"
        )

    missing = [k for k in _REQUIRED_FIELDS if k not in raw]
    if missing:
        raise ValueError(
            f"OCR response missing required fields {missing}; image={image_path}; raw={raw!r}"
        )

    supplier_biznum = str(raw["supplier_biznum"]).strip()
    buyer_biznum = str(raw["buyer_biznum"]).strip()
    if not validate_biznum(supplier_biznum):
        raise ValueError(
            f"invalid supplier_biznum checksum: {supplier_biznum!r}; image={image_path}"
        )
    if not validate_biznum(buyer_biznum):
        raise ValueError(f"invalid buyer_biznum checksum: {buyer_biznum!r}; image={image_path}")

    total_supply = _to_int(raw["total_supply"])
    total_vat = _to_int(raw["total_vat"])
    total_amount = _to_int(raw["total_amount"])

    # 면세(vat=0) 또는 일반(vat = supply // 10) 둘 중 하나여야 함.
    expected_vat = total_supply // 10
    if total_vat != 0 and total_vat != expected_vat:
        raise ValueError(
            f"vat mismatch: total_vat={total_vat:,} but expected "
            f"{expected_vat:,} (= total_supply {total_supply:,} // 10); "
            f"image={image_path}"
        )

    line_items = _normalize_line_items(raw.get("line_items", []))

    return InvoiceData(
        invoice_no=str(raw["invoice_no"]).strip(),
        issue_date=str(raw["issue_date"]).strip(),
        supplier_biznum=supplier_biznum,
        supplier_name=str(raw["supplier_name"]).strip(),
        buyer_biznum=buyer_biznum,
        buyer_name=str(raw["buyer_name"]).strip(),
        line_items=line_items,
        total_supply=total_supply,
        total_vat=total_vat,
        total_amount=total_amount,
    )


# Placeholder biznum used inside SAFE-FALLBACK InvoiceData. 알고리즘으로 사전 검증된
# 공개값(삼성전자 220-81-62517) — 시연 placeholder가 다시 ``validate_biznum``을 통과해야
# downstream에서 fallback path가 깨지지 않는다.
_VALID_PLACEHOLDER_BIZNUM: str = "220-81-62517"


def _to_int(value: Any) -> int:
    """숫자/문자열 → 정수.

    처리:
        - ``int`` 그대로 (``bool`` 차단).
        - ``float`` truncate.
        - 통화 기호(``₩``), 콤마, ``원`` suffix, whitespace 제거.
        - 소수점 입력은 정수부만 사용.

    Raises:
        ValueError: 숫자로 변환 불가능한 입력.
    """
    if isinstance(value, bool):
        raise ValueError(f"cannot parse int: {value!r}")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    s = str(value).strip()
    # 통화 기호/콤마/원 suffix/공백 제거
    for ch in ("₩", ",", "원", " ", "\t"):
        s = s.replace(ch, "")
    if "." in s:
        s = s.split(".")[0]
    if not s or s == "-":
        raise ValueError(f"cannot parse int: {value!r}")
    try:
        return int(s)
    except ValueError as e:
        raise ValueError(f"cannot parse int: {value!r}") from e


def _normalize_line_items(items: Any) -> list[dict[str, Any]]:
    """line_items의 qty/unit_price/amount를 정수로 정규화.

    실패 채널 (item 단위는 silent):
        - dict이 아닌 항목은 결과에서 제외.
        - 숫자 변환 실패 시 0으로 fallback (item 전체를 깨뜨리지 않음).
    """
    if not isinstance(items, list):
        return []
    out: list[dict[str, Any]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        normalized: dict[str, Any] = {}
        if "name" in it:
            normalized["name"] = str(it["name"]).strip()
        for num_key in ("qty", "unit_price", "amount"):
            if num_key in it:
                try:
                    normalized[num_key] = _to_int(it[num_key])
                except ValueError:
                    normalized[num_key] = 0
        out.append(normalized)
    return out
