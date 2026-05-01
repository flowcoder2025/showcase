"""case08용 가상 세금계산서 이미지 30장 생성.

R3-O1 (self-OCR risk 회피): Gemma 4 E4B가 합성 텍스트를 100% 맞추지 못하도록
점 노이즈 + Gaussian blur + 살짝 회전을 적용한다. E4B는 E2B보다 정확도가 높지만
30장 budget으로 처리 시간이 늘어나도록 image 수를 100→30으로 축소했다.

Usage:
    uv run python personas/sample_data/generate_invoices.py

Output:
    personas/sample_data/invoices_scanned/inv_001.png ~ inv_030.png  (30장 PNG)
    personas/sample_data/invoices_scanned/_ground_truth.json         (정답 metadata)

Determinism:
    Faker seed=42, random.seed(42) → 동일 입력에서 동일 30장 생성.

Mix:
    - 25장: 정상 (일반세 vat = supply // 10), 양쪽 biznum 모두 valid.
    - 3장 면세: vat=0 (의료/교육/도서 등 면세 거래 representation).
    - 2장 invalid biznum: 공급자 또는 공급받는자 사업자번호 체크섬 깨짐
      (verified/failed split이 demo에서 non-trivial하도록).
"""

from __future__ import annotations

import json
import random
from datetime import date
from pathlib import Path
from typing import Any

from dateutil.relativedelta import relativedelta
from faker import Faker
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# 한국 사업자번호 체크섬 가중치 (core.ocr.invoice._BIZNUM_WEIGHTS와 동일).
_BIZNUM_WEIGHTS: tuple[int, ...] = (1, 3, 7, 1, 3, 7, 1, 3, 5)

_FONT_CANDIDATES: tuple[str, ...] = (
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
)

# 면세 품목 prefix — vat=0 케이스에서 라인아이템 이름으로 사용.
_TAX_FREE_ITEMS: tuple[str, ...] = (
    "도서 출판물",
    "의료 진단 서비스",
    "교육 강의",
    "농산물 직거래",
)

# 일반 품목 prefix.
_TAXABLE_ITEMS: tuple[str, ...] = (
    "사무용품 일괄",
    "전자부품 모듈",
    "포장재 박스",
    "OA 소모품",
    "산업용 윤활유",
    "공구 세트",
    "유니폼 단체",
    "프린터 토너",
)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """한글 시스템 폰트 시도 → 모두 실패 시 PIL default."""
    for candidate in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _generate_valid_biznum(rng: random.Random) -> str:
    """체크섬을 만족하는 임의의 사업자번호 (XXX-XX-XXXXX 형식).

    앞 9자리는 무작위, 10번째 자리는 모듈러스 알고리즘으로 계산한다.
    """
    nums = [rng.randint(0, 9) for _ in range(9)]
    total = sum(d * w for d, w in zip(nums, _BIZNUM_WEIGHTS, strict=True))
    total += (nums[8] * 5) // 10
    check = (10 - (total % 10)) % 10
    nums.append(check)
    s = "".join(str(d) for d in nums)
    return f"{s[:3]}-{s[3:5]}-{s[5:]}"


def _corrupt_biznum(valid: str, rng: random.Random) -> str:
    """체크섬을 의도적으로 깨뜨린다 (검증 실패 케이스 생성용)."""
    digits = list(valid.replace("-", ""))
    idx = rng.randint(0, 8)  # 마지막 자리는 건드리지 않음 — 다른 자리를 흔들어 mismatch 유도
    new_digit = (int(digits[idx]) + rng.randint(1, 9)) % 10
    digits[idx] = str(new_digit)
    s = "".join(digits)
    return f"{s[:3]}-{s[3:5]}-{s[5:]}"


def _add_noise(img: Image.Image, rng: random.Random) -> Image.Image:
    """점 노이즈 + 약한 Gaussian blur. case07 receipts와 동일 정책 (R3-O1)."""
    pixels = img.load()
    if pixels is None:  # pragma: no cover — Pillow 계약상 발생 안 함
        return img
    width, height = img.size
    for _ in range(rng.randint(400, 900)):
        x = rng.randint(0, width - 1)
        y = rng.randint(0, height - 1)
        gray = rng.randint(0, 80)
        pixels[x, y] = (gray, gray, gray)
    return img.filter(ImageFilter.GaussianBlur(0.4))


def _make_invoice(
    idx: int,
    fake: Faker,
    rng: random.Random,
    *,
    tax_free: bool,
    corrupt_supplier: bool,
    corrupt_buyer: bool,
    base_date: date,
) -> tuple[Image.Image, dict[str, Any]]:
    """세금계산서 1장 + 정답 metadata 생성."""
    width, height = 720, 520
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    title_font = _font(28)
    label_font = _font(15)
    body_font = _font(14)

    supplier_biznum_valid = _generate_valid_biznum(rng)
    buyer_biznum_valid = _generate_valid_biznum(rng)
    supplier_biznum = (
        _corrupt_biznum(supplier_biznum_valid, rng) if corrupt_supplier else supplier_biznum_valid
    )
    buyer_biznum = _corrupt_biznum(buyer_biznum_valid, rng) if corrupt_buyer else buyer_biznum_valid

    supplier_name = fake.company()
    buyer_name = fake.company()
    invoice_no = f"INV-2026-{idx + 1:05d}"
    issue_date = base_date.strftime("%Y-%m-%d")

    # 라인 아이템 1~3개. 면세이면 면세 품목 사용.
    n_items = rng.randint(1, 3)
    item_pool = _TAX_FREE_ITEMS if tax_free else _TAXABLE_ITEMS
    items: list[dict[str, Any]] = []
    total_supply = 0
    for _ in range(n_items):
        name = rng.choice(item_pool)
        qty = rng.randint(1, 5)
        unit_price = rng.choice(
            [10_000, 25_000, 50_000, 80_000, 120_000, 200_000, 350_000, 500_000]
        )
        amount = qty * unit_price
        items.append({"name": name, "qty": qty, "unit_price": unit_price, "amount": amount})
        total_supply += amount

    total_vat = 0 if tax_free else total_supply // 10
    total_amount = total_supply + total_vat

    # 그리기.
    draw.text((width // 2 - 70, 16), "세금계산서", font=title_font, fill="black")

    y = 70
    draw.text((24, y), f"거래번호: {invoice_no}", font=body_font, fill="black")
    draw.text((width - 220, y), f"작성일자: {issue_date}", font=body_font, fill="black")

    y += 36
    draw.text((24, y), "[ 공급자 ]", font=label_font, fill="black")
    y += 22
    draw.text((24, y), f"등록번호: {supplier_biznum}", font=body_font, fill="black")
    y += 22
    draw.text((24, y), f"상호: {supplier_name}", font=body_font, fill="black")

    y += 36
    draw.text((24, y), "[ 공급받는자 ]", font=label_font, fill="black")
    y += 22
    draw.text((24, y), f"등록번호: {buyer_biznum}", font=body_font, fill="black")
    y += 22
    draw.text((24, y), f"상호: {buyer_name}", font=body_font, fill="black")

    y += 36
    # 품목 표 헤더
    draw.text((24, y), "품목", font=label_font, fill="black")
    draw.text((280, y), "수량", font=label_font, fill="black")
    draw.text((360, y), "단가", font=label_font, fill="black")
    draw.text((520, y), "공급가액", font=label_font, fill="black")
    y += 22
    for it in items:
        draw.text((24, y), str(it["name"]), font=body_font, fill="black")
        draw.text((280, y), str(it["qty"]), font=body_font, fill="black")
        draw.text((360, y), f"{it['unit_price']:,}", font=body_font, fill="black")
        draw.text((520, y), f"{it['amount']:,}", font=body_font, fill="black")
        y += 22

    y += 18
    draw.text((24, y), f"공급가액: {total_supply:,}원", font=label_font, fill="black")
    y += 22
    if tax_free:
        draw.text((24, y), "세액: 면세 (0원)", font=label_font, fill="black")
    else:
        draw.text((24, y), f"세액: {total_vat:,}원", font=label_font, fill="black")
    y += 22
    draw.text((24, y), f"합계: {total_amount:,}원", font=title_font, fill="black")

    # 노이즈 + 약한 회전.
    img = _add_noise(img, rng)
    img = img.rotate(rng.uniform(-1.5, 1.5), fillcolor="white", expand=False)

    metadata: dict[str, Any] = {
        "filename": f"inv_{idx + 1:03d}.png",
        "invoice_no": invoice_no,
        "issue_date": issue_date,
        "supplier_biznum": supplier_biznum,
        "supplier_biznum_valid": supplier_biznum_valid,
        "supplier_name": supplier_name,
        "buyer_biznum": buyer_biznum,
        "buyer_biznum_valid": buyer_biznum_valid,
        "buyer_name": buyer_name,
        "line_items": items,
        "total_supply": total_supply,
        "total_vat": total_vat,
        "total_amount": total_amount,
        "tax_free": tax_free,
        "corrupt_supplier": corrupt_supplier,
        "corrupt_buyer": corrupt_buyer,
    }
    return img, metadata


def main() -> None:
    fake = Faker("ko_KR")
    Faker.seed(42)
    rng = random.Random(42)

    out_dir = Path(__file__).parent / "invoices_scanned"
    out_dir.mkdir(exist_ok=True)

    # 30장 분배: 25 정상 + 3 면세 + 2 invalid biznum.
    # 인덱스 분포 (deterministic):
    #   tax_free: idx in {7, 14, 22}
    #   corrupt_supplier: idx == 4
    #   corrupt_buyer: idx == 19
    tax_free_indices: frozenset[int] = frozenset({7, 14, 22})
    corrupt_supplier_indices: frozenset[int] = frozenset({4})
    corrupt_buyer_indices: frozenset[int] = frozenset({19})

    # 12개월 spread (T11.5 lesson: relativedelta, NOT timedelta(days=30*offset)).
    base = date(2026, 4, 1)

    truth: list[dict[str, Any]] = []
    for i in range(30):
        month_offset = i % 12  # 12개월에 걸쳐 분포
        issue_dt = base - relativedelta(months=month_offset)
        img, meta = _make_invoice(
            i,
            fake,
            rng,
            tax_free=i in tax_free_indices,
            corrupt_supplier=i in corrupt_supplier_indices,
            corrupt_buyer=i in corrupt_buyer_indices,
            base_date=issue_dt,
        )
        path = out_dir / meta["filename"]
        img.save(path, optimize=True)
        truth.append(meta)

    truth_path = out_dir / "_ground_truth.json"
    truth_path.write_text(
        json.dumps(truth, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Generated 30 invoices -> {out_dir}/")
    print(f"  Ground truth -> {truth_path}")


if __name__ == "__main__":
    main()
