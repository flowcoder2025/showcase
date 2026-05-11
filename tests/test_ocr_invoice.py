"""T14: core.ocr.invoice — 세금계산서 OCR + biznum 모듈러스 + 회계 CSV 검증.

대부분 ``gemma.extract`` mock 기반. 실제 Ollama 호출 없음.

NOTE: known-valid 사업자번호는 알고리즘으로 사전 검증한 공개값 사용 (220-81-62517 삼성전자,
120-81-47521 카카오). plan v2의 예시 ``104-81-32402``는 알고리즘으로 검증 시 fail —
T14 진입 시 수정 (deviation 기록).
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import pytest
from flowcoder_office_tools.ocr import gemma, invoice

# 알고리즘 검증된 known-valid 공개 사업자번호.
_VALID_SUPPLIER = "220-81-62517"  # 삼성전자
_VALID_BUYER = "120-81-47521"  # 카카오


# -- validate_biznum --------------------------------------------------------


def test_validate_biznum_known_valid() -> None:
    """알고리즘으로 사전 검증된 공개 사업자번호 (삼성전자)."""
    assert invoice.validate_biznum("220-81-62517") is True


def test_validate_biznum_known_valid_kakao() -> None:
    """알고리즘으로 사전 검증된 공개 사업자번호 (카카오)."""
    assert invoice.validate_biznum("120-81-47521") is True


def test_validate_biznum_invalid_checksum() -> None:
    """체크섬만 다른 한 글자 → False."""
    assert invoice.validate_biznum("220-81-62518") is False


def test_validate_biznum_wrong_length_short() -> None:
    assert invoice.validate_biznum("123-45") is False


def test_validate_biznum_wrong_length_long() -> None:
    assert invoice.validate_biznum("12345678901") is False


def test_validate_biznum_with_dashes() -> None:
    """``-`` 포함 / 미포함 모두 동일 결과."""
    assert invoice.validate_biznum("220-81-62517") is True
    assert invoice.validate_biznum("2208162517") is True


def test_validate_biznum_with_non_digits() -> None:
    """숫자가 아닌 문자가 섞이면 False."""
    assert invoice.validate_biznum("12345abcde0") is False


def test_validate_biznum_empty_string() -> None:
    assert invoice.validate_biznum("") is False


def test_validate_biznum_strips_whitespace() -> None:
    """앞뒤 공백은 strip 후 검증 — OCR 결과의 trailing 공백 robust 처리."""
    assert invoice.validate_biznum(" 220-81-62517 ") is True
    assert invoice.validate_biznum("\t2208162517\n") is True


def test_validate_biznum_internal_whitespace_rejected() -> None:
    """내부 공백/기타 구분자는 strip 대상이 아님 — 엄격한 형식만 허용."""
    assert invoice.validate_biznum("220 81 62517") is False
    assert invoice.validate_biznum("220.81.62517") is False


# -- extract: contract via gemma.extract mock -------------------------------


def _fake_invoice(
    *,
    supplier: str = _VALID_SUPPLIER,
    buyer: str = _VALID_BUYER,
    total_supply: int = 1_000_000,
    total_vat: int | None = None,
    total_amount: int | None = None,
) -> dict[str, Any]:
    """plan v2 §13 fake fixture — supplier·buyer 모두 valid biznum 보장."""
    if total_vat is None:
        total_vat = total_supply // 10
    if total_amount is None:
        total_amount = total_supply + total_vat
    return {
        "invoice_no": "INV-2026-00042",
        "issue_date": "2026-05-01",
        "supplier_biznum": supplier,
        "supplier_name": "AX상사",
        "buyer_biznum": buyer,
        "buyer_name": "콩코드",
        "line_items": [
            {"name": "강철 파이프 6m", "qty": 100, "unit_price": 10000, "amount": 1_000_000}
        ],
        "total_supply": total_supply,
        "total_vat": total_vat,
        "total_amount": total_amount,
    }


def _mock_gemma(monkeypatch: pytest.MonkeyPatch, payload: dict[str, Any]) -> list[dict[str, Any]]:
    """``gemma.extract`` mock + 호출 인자 캡처."""
    calls: list[dict[str, Any]] = []

    def _fake(image_path: Path | str, **kwargs: Any) -> dict[str, Any]:
        calls.append({"image_path": image_path, **kwargs})
        return payload

    monkeypatch.setattr(gemma, "extract", _fake)
    return calls


def test_extract_invoice_returns_typed_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    """주요 필드 + biznum valid + vat == supply // 10 검증."""
    _mock_gemma(monkeypatch, _fake_invoice())
    result = invoice.extract("/tmp/inv.png")

    # TypedDict 키 모두 존재
    for key in (
        "invoice_no",
        "issue_date",
        "supplier_biznum",
        "supplier_name",
        "buyer_biznum",
        "buyer_name",
        "line_items",
        "total_supply",
        "total_vat",
        "total_amount",
    ):
        assert key in result, f"missing key: {key}"

    assert invoice.validate_biznum(result["supplier_biznum"])
    assert invoice.validate_biznum(result["buyer_biznum"])
    assert result["total_vat"] == result["total_supply"] // 10
    assert result["total_amount"] == result["total_supply"] + result["total_vat"]


def test_extract_uses_e4b_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """case08는 정확도 우선 → E4B 모델 호출."""
    calls = _mock_gemma(monkeypatch, _fake_invoice())
    invoice.extract("/tmp/inv.png")
    assert calls[0]["model"] == "gemma4:e4b"


def test_extract_passes_invoice_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _mock_gemma(monkeypatch, _fake_invoice())
    invoice.extract("/tmp/inv.png")
    assert calls[0]["schema"] is invoice.INVOICE_SCHEMA


def test_extract_tax_free_invoice(monkeypatch: pytest.MonkeyPatch) -> None:
    """면세 invoice (vat=0, supply>0) → 정상 통과 (raise 안 함)."""
    _mock_gemma(
        monkeypatch,
        _fake_invoice(total_supply=1_000_000, total_vat=0, total_amount=1_000_000),
    )
    result = invoice.extract("/tmp/inv.png")
    assert result["total_vat"] == 0
    assert result["total_supply"] == 1_000_000


def test_extract_invalid_supplier_biznum_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """공급자 사업자번호 체크섬 fail → ValueError."""
    _mock_gemma(monkeypatch, _fake_invoice(supplier="123-45-67890"))
    with pytest.raises(ValueError) as exc_info:
        invoice.extract("/tmp/inv.png")
    assert "supplier_biznum" in str(exc_info.value)


def test_extract_invalid_buyer_biznum_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """공급받는자 사업자번호 체크섬 fail → ValueError."""
    _mock_gemma(monkeypatch, _fake_invoice(buyer="123-45-67890"))
    with pytest.raises(ValueError) as exc_info:
        invoice.extract("/tmp/inv.png")
    assert "buyer_biznum" in str(exc_info.value)


def test_extract_vat_mismatch_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """vat != supply//10 + 면세도 아님 → ValueError."""
    _mock_gemma(
        monkeypatch,
        _fake_invoice(total_supply=1_000_000, total_vat=50_000, total_amount=1_050_000),
    )
    with pytest.raises(ValueError) as exc_info:
        invoice.extract("/tmp/inv.png")
    msg = str(exc_info.value)
    assert "vat" in msg.lower()


def test_validate_invoice_vat_tolerance_one_won(monkeypatch: pytest.MonkeyPatch) -> None:
    """R2-H3 regression: ``total_supply // 10`` truncate로 인한 1원 차이 false
    positive 방지. supply=1005 일 때 banker's rounding으로 vat=101 이 정상이지만,
    이전 버전은 ``1005 // 10 = 100`` 로 맞지 않아 reject했다.
    수정 후: ±1원 허용으로 정상 통과해야 한다.
    """
    _mock_gemma(
        monkeypatch,
        _fake_invoice(total_supply=1005, total_vat=101, total_amount=1106),
    )
    # 예외 없이 정상 통과하면 OK.
    result = invoice.extract("/tmp/inv.png")
    assert result["total_supply"] == 1005
    assert result["total_vat"] == 101


def test_validate_invoice_vat_tolerance_rejects_two_won_diff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R2-H3: ±1원 허용은 OCR rounding noise 한정. 2원 이상 차이는 여전히 reject."""
    _mock_gemma(
        monkeypatch,
        _fake_invoice(total_supply=1000, total_vat=102, total_amount=1102),
    )
    with pytest.raises(ValueError) as exc_info:
        invoice.extract("/tmp/inv.png")
    assert "vat" in str(exc_info.value).lower()


def test_extract_safe_fallback_returns_placeholder(monkeypatch: pytest.MonkeyPatch) -> None:
    """gemma safe_dummy → InvoiceData placeholder (시연 흐름 보호)."""
    _mock_gemma(monkeypatch, {"_safe": True, "image_hash": "deadbeef"})
    result = invoice.extract("/tmp/inv.png")
    assert result["invoice_no"] == "[SAFE-FALLBACK]"
    assert result["total_supply"] == 0
    assert result["total_vat"] == 0
    assert result["total_amount"] == 0
    assert "deadbeef" in result["supplier_name"] or "deadbeef" in result["buyer_name"]


def test_extract_parse_error_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_gemma(
        monkeypatch,
        {"_raw_text": "garbage", "_parse_error": "JSON decode failed"},
    )
    with pytest.raises(ValueError) as exc_info:
        invoice.extract("/tmp/inv.png")
    assert "garbage" in str(exc_info.value)


def test_extract_missing_required_field_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """필수 필드 missing → ValueError + 해당 필드명 포함."""
    _mock_gemma(
        monkeypatch,
        {
            "invoice_no": "X",
            "issue_date": "2026-05-01",
            # supplier_biznum / buyer_biznum 누락
            "supplier_name": "AX",
            "buyer_name": "B",
            "line_items": [],
            "total_supply": 100,
            "total_vat": 10,
            "total_amount": 110,
        },
    )
    with pytest.raises(ValueError) as exc_info:
        invoice.extract("/tmp/inv.png")
    msg = str(exc_info.value)
    assert "supplier_biznum" in msg or "buyer_biznum" in msg


# -- to_accounting_csv ------------------------------------------------------


def test_to_accounting_csv_utf8(tmp_path: Path) -> None:
    """utf-8 인코딩으로 작성 + 헤더 + 데이터 row 포함."""
    inv = _fake_invoice()
    out = tmp_path / "ledger.csv"

    # InvoiceData TypedDict로 변환 (extract와 동일 정규화 후 통과 보장)
    invoices: list[invoice.InvoiceData] = [
        invoice.InvoiceData(
            invoice_no=inv["invoice_no"],
            issue_date=inv["issue_date"],
            supplier_biznum=inv["supplier_biznum"],
            supplier_name=inv["supplier_name"],
            buyer_biznum=inv["buyer_biznum"],
            buyer_name=inv["buyer_name"],
            line_items=inv["line_items"],
            total_supply=inv["total_supply"],
            total_vat=inv["total_vat"],
            total_amount=inv["total_amount"],
        )
    ]

    invoice.to_accounting_csv(invoices, out, encoding="utf-8")
    assert out.exists()

    rows = list(csv.reader(out.open(encoding="utf-8")))
    assert rows[0] == [
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
    assert rows[1][0] == "2026-05-01"
    assert rows[1][1] == "INV-2026-00042"
    assert rows[1][3] == "AX상사"


def test_to_accounting_csv_cp949_encoding(tmp_path: Path) -> None:
    """CSV cp949 인코딩 옵션 — 회계SW (더존, 영림원) 호환."""
    inv = _fake_invoice()
    out = tmp_path / "ledger_cp949.csv"

    invoices: list[invoice.InvoiceData] = [
        invoice.InvoiceData(
            invoice_no=inv["invoice_no"],
            issue_date=inv["issue_date"],
            supplier_biznum=inv["supplier_biznum"],
            supplier_name=inv["supplier_name"],
            buyer_biznum=inv["buyer_biznum"],
            buyer_name=inv["buyer_name"],
            line_items=inv["line_items"],
            total_supply=inv["total_supply"],
            total_vat=inv["total_vat"],
            total_amount=inv["total_amount"],
        )
    ]

    invoice.to_accounting_csv(invoices, out, encoding="cp949")
    assert out.exists()

    text = out.read_text(encoding="cp949")
    assert "거래일" in text
    assert "공급자번호" in text
    assert "AX상사" in text


def test_to_accounting_csv_empty_list(tmp_path: Path) -> None:
    """빈 invoices도 헤더만 작성하고 정상 종료."""
    out = tmp_path / "empty.csv"
    invoice.to_accounting_csv([], out, encoding="utf-8")
    assert out.exists()
    rows = list(csv.reader(out.open(encoding="utf-8")))
    assert len(rows) == 1
    assert rows[0][0] == "거래일"


def test_to_accounting_csv_accepts_string_path(tmp_path: Path) -> None:
    """out_path가 str로 전달돼도 정상 작동."""
    out = tmp_path / "string_path.csv"
    invoice.to_accounting_csv([], str(out), encoding="utf-8")
    assert out.exists()


def test_to_accounting_csv_unsupported_cp949_char_raises(tmp_path: Path) -> None:
    """cp949에 없는 문자(이모지) → UnicodeEncodeError raise (SI 호환 fail-fast)."""
    inv = _fake_invoice()
    inv_typed = invoice.InvoiceData(
        invoice_no=inv["invoice_no"],
        issue_date=inv["issue_date"],
        supplier_biznum=inv["supplier_biznum"],
        supplier_name="AX상사 🚀",  # 이모지 — cp949 미지원
        buyer_biznum=inv["buyer_biznum"],
        buyer_name=inv["buyer_name"],
        line_items=inv["line_items"],
        total_supply=inv["total_supply"],
        total_vat=inv["total_vat"],
        total_amount=inv["total_amount"],
    )
    out = tmp_path / "bad.csv"
    with pytest.raises(UnicodeEncodeError):
        invoice.to_accounting_csv([inv_typed], out, encoding="cp949")


def test_to_accounting_csv_utf8_with_bom(tmp_path: Path) -> None:
    """``bom=True`` + utf-8 → 파일 앞에 ``EF BB BF`` BOM 기록 (Windows Excel 호환)."""
    inv = _fake_invoice()
    inv_typed = invoice.InvoiceData(
        invoice_no=inv["invoice_no"],
        issue_date=inv["issue_date"],
        supplier_biznum=inv["supplier_biznum"],
        supplier_name=inv["supplier_name"],
        buyer_biznum=inv["buyer_biznum"],
        buyer_name=inv["buyer_name"],
        line_items=inv["line_items"],
        total_supply=inv["total_supply"],
        total_vat=inv["total_vat"],
        total_amount=inv["total_amount"],
    )
    out = tmp_path / "ledger_bom.csv"
    invoice.to_accounting_csv([inv_typed], out, encoding="utf-8", bom=True)

    # 1. raw bytes 시작이 BOM(EF BB BF) 인지 확인.
    raw = out.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf"), f"BOM missing; first bytes={raw[:6]!r}"

    # 2. utf-8-sig 로 읽으면 BOM 자동 제거 + 컨텐츠 정상.
    text = out.read_text(encoding="utf-8-sig")
    assert "거래일" in text
    assert "AX상사" in text
    assert "INV-2026-00042" in text


def test_to_accounting_csv_no_bom_default(tmp_path: Path) -> None:
    """기본(``bom=False``) → BOM 바이트 없음 (기존 동작 보존)."""
    inv = _fake_invoice()
    inv_typed = invoice.InvoiceData(
        invoice_no=inv["invoice_no"],
        issue_date=inv["issue_date"],
        supplier_biznum=inv["supplier_biznum"],
        supplier_name=inv["supplier_name"],
        buyer_biznum=inv["buyer_biznum"],
        buyer_name=inv["buyer_name"],
        line_items=inv["line_items"],
        total_supply=inv["total_supply"],
        total_vat=inv["total_vat"],
        total_amount=inv["total_amount"],
    )
    out = tmp_path / "ledger_no_bom.csv"
    invoice.to_accounting_csv([inv_typed], out, encoding="utf-8")

    raw = out.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), "BOM should not be present by default"


def test_to_accounting_csv_bom_with_cp949_raises(tmp_path: Path) -> None:
    """cp949에는 BOM 개념이 없음 → ``bom=True`` 조합은 ValueError (fail-fast)."""
    out = tmp_path / "should_not_exist.csv"
    with pytest.raises(ValueError) as exc_info:
        invoice.to_accounting_csv([], out, encoding="cp949", bom=True)
    assert "BOM" in str(exc_info.value)
    assert "utf-8" in str(exc_info.value)
    assert not out.exists(), "file should not be created when validation fails"


# -- T15.5: column_map override --------------------------------------------


def _typed_fake_invoice() -> invoice.InvoiceData:
    """to_accounting_csv 입력용 InvoiceData fixture."""
    inv = _fake_invoice()
    return invoice.InvoiceData(
        invoice_no=inv["invoice_no"],
        issue_date=inv["issue_date"],
        supplier_biznum=inv["supplier_biznum"],
        supplier_name=inv["supplier_name"],
        buyer_biznum=inv["buyer_biznum"],
        buyer_name=inv["buyer_name"],
        line_items=inv["line_items"],
        total_supply=inv["total_supply"],
        total_vat=inv["total_vat"],
        total_amount=inv["total_amount"],
    )


def test_to_accounting_csv_column_map_partial(tmp_path: Path) -> None:
    """부분 컬럼 + 영문 헤더 — 누락된 슬러그는 CSV에서 제외된다."""
    inv_typed = _typed_fake_invoice()
    out = tmp_path / "partial.csv"
    invoice.to_accounting_csv(
        [inv_typed],
        out,
        encoding="utf-8",
        column_map={"issue_date": "Date", "total_amount": "Total"},
    )

    rows = list(csv.reader(out.open(encoding="utf-8")))
    assert rows[0] == ["Date", "Total"]
    assert rows[1] == ["2026-05-01", "1100000"]
    assert len(rows[1]) == 2  # 다른 컬럼은 포함되지 않음


def test_to_accounting_csv_column_map_reordered(tmp_path: Path) -> None:
    """전체 9개 키, 다른 순서 + custom 헤더 — dict 삽입 순서 보존."""
    inv_typed = _typed_fake_invoice()
    out = tmp_path / "reordered.csv"
    custom = {
        "invoice_no": "전표번호",
        "issue_date": "전표일자",
        "total_amount": "합계금액",
        "total_vat": "세액",
        "total_supply": "공급가",
        "supplier_biznum": "공급자등록번호",
        "supplier_name": "공급자상호",
        "buyer_biznum": "매입자등록번호",
        "buyer_name": "매입자상호",
    }
    invoice.to_accounting_csv([inv_typed], out, encoding="utf-8", column_map=custom)

    rows = list(csv.reader(out.open(encoding="utf-8")))
    assert rows[0] == list(custom.values())
    # 첫 두 컬럼이 invoice_no, issue_date 순서로 재배치돼야 한다.
    assert rows[1][0] == "INV-2026-00042"
    assert rows[1][1] == "2026-05-01"


def test_to_accounting_csv_column_map_empty_raises(tmp_path: Path) -> None:
    """빈 column_map은 default와 의미가 다르므로 ValueError (실수 방지)."""
    out = tmp_path / "empty_map.csv"
    with pytest.raises(ValueError) as exc_info:
        invoice.to_accounting_csv([], out, column_map={})
    assert "empty" in str(exc_info.value).lower()
    assert not out.exists()


def test_to_accounting_csv_column_map_invalid_key_raises(tmp_path: Path) -> None:
    """canonical 슬러그 외의 키는 ValueError + 키 이름 포함."""
    out = tmp_path / "bad_key.csv"
    with pytest.raises(ValueError) as exc_info:
        invoice.to_accounting_csv([], out, column_map={"foo": "Bar"})
    assert "foo" in str(exc_info.value)
    assert "unknown column" in str(exc_info.value)
    assert not out.exists()


def test_to_accounting_csv_column_map_with_bom(tmp_path: Path) -> None:
    """column_map + bom=True/utf-8 조합 — BOM이 정상 작성되고 컬럼도 적용된다."""
    inv_typed = _typed_fake_invoice()
    out = tmp_path / "map_bom.csv"
    invoice.to_accounting_csv(
        [inv_typed],
        out,
        encoding="utf-8",
        bom=True,
        column_map={"issue_date": "날짜", "invoice_no": "번호"},
    )

    raw = out.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    text = out.read_text(encoding="utf-8-sig")
    assert text.splitlines()[0] == "날짜,번호"
    assert "2026-05-01,INV-2026-00042" in text
