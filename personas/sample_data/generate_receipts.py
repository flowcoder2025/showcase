"""case07용 가상 영수증 이미지 100장 생성.

R3-O1 (self-OCR risk 회피): Gemma 4가 합성 텍스트를 100% 맞추지 못하도록
점 노이즈 + Gaussian blur + ±2.5° 회전을 적용한다. 그래도 합성 데이터 자기충족
가능성은 남아있으며 (R2-M2 High), 실 영수증 hold-out 검증으로 보완해야 한다.

Usage:
    uv run python personas/sample_data/generate_receipts.py

Output:
    personas/sample_data/receipts/r001.png ~ r100.png  (100장 PNG)
    personas/sample_data/receipts/_ground_truth.json   (정답 metadata)

Determinism:
    Faker seed=42, random.seed(42) → 동일 입력에서 동일 100장 생성.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from faker import Faker
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# 가맹점 패턴 — case07 scenario._CATEGORY_BY_MERCHANT_PREFIX와 동기화.
MERCHANT_PATTERNS: tuple[str, ...] = (
    "스타벅스 강남점",
    "이디야 역삼",
    "투썸 종로",
    "할리스 광화문",
    "백다방 신촌",
    "맥도날드 강남대로",
    "버거킹 잠실",
    "롯데마트 송파",
    "이마트 트레이더스 김포",
    "GS25 서초",
    "CU 청담",
    "세븐일레븐 합정",
)

CATEGORY_BY_PREFIX: dict[str, str] = {
    "스타벅스": "커피",
    "이디야": "커피",
    "투썸": "커피",
    "할리스": "커피",
    "백다방": "커피",
    "맥도날드": "식사",
    "버거킹": "식사",
    "롯데마트": "장보기",
    "이마트": "장보기",
    "GS25": "편의점",
    "CU": "편의점",
    "세븐일레븐": "편의점",
}

PAYMENT_METHODS: tuple[str, ...] = ("현금", "신용카드", "삼성페이", "네이버페이")

# 한글 폰트 후보 — 시스템에 없으면 default font fallback (테스트 환경 호환).
_FONT_CANDIDATES: tuple[str, ...] = (
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """한글 시스템 폰트 시도 → 모두 실패 시 PIL default."""
    for candidate in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _category_for(merchant: str) -> str:
    for prefix, category in CATEGORY_BY_PREFIX.items():
        if merchant.startswith(prefix):
            return category
    return "기타"


def _add_noise(img: Image.Image) -> Image.Image:
    """점 노이즈 + Gaussian blur — OCR이 100% 정답을 맞추지 못하게."""
    pixels = img.load()
    if pixels is None:  # pragma: no cover — Pillow 계약상 발생 안 함
        return img
    width, height = img.size
    for _ in range(random.randint(300, 800)):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        gray = random.randint(0, 80)
        pixels[x, y] = (gray, gray, gray)
    return img.filter(ImageFilter.GaussianBlur(0.4))


def _make_receipt(idx: int, fake: Faker) -> tuple[Image.Image, dict[str, Any]]:
    """영수증 이미지 1장 + 정답 metadata 생성."""
    width, height = 400, 600
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    title_font = _font(22)
    body_font = _font(14)

    merchant = random.choice(MERCHANT_PATTERNS)
    category = _category_for(merchant)
    date_dt = fake.date_between(start_date="-90d", end_date="today")
    date_str = date_dt.strftime("%Y-%m-%d")
    n_items = random.randint(1, 4)
    items: list[dict[str, Any]] = []
    total = 0
    for _ in range(n_items):
        # fake.bs()는 영문 비즈니스 buzzword — 시연 가시성보다 결정성이 우선.
        name = fake.bs().split()[0]
        qty = random.randint(1, 3)
        price = random.choice([3_500, 4_500, 5_500, 6_900, 12_000, 18_000])
        items.append({"name": name, "qty": qty, "price": price})
        total += qty * price
    payment = random.choice(PAYMENT_METHODS)

    # 영수증 본문 그리기
    y = 30
    draw.text((width // 2 - 60, y), merchant, font=title_font, fill="black")
    y += 50
    draw.text((30, y), f"날짜: {date_str}", font=body_font, fill="black")
    y += 30
    for it in items:
        draw.text((30, y), f"{it['name']}  x{it['qty']}", font=body_font, fill="black")
        amount_text = f"{int(it['price']) * int(it['qty']):,}"
        draw.text((width - 100, y), amount_text, font=body_font, fill="black")
        y += 25
    y += 20
    draw.text((30, y), f"합계: {total:,}원", font=title_font, fill="black")
    y += 40
    draw.text((30, y), f"결제: {payment}", font=body_font, fill="black")

    # 노이즈/회전 (R3-O1)
    img = _add_noise(img)
    img = img.rotate(random.uniform(-2.5, 2.5), fillcolor="white", expand=False)

    metadata: dict[str, Any] = {
        "merchant": merchant,
        "category": category,
        "date": date_str,
        "amount": total,
        "items": items,
        "payment_method": payment,
    }
    return img, metadata


def main() -> None:
    fake = Faker("ko_KR")
    Faker.seed(42)
    random.seed(42)

    out_dir = Path(__file__).parent / "receipts"
    out_dir.mkdir(exist_ok=True)

    truth: list[dict[str, Any]] = []
    for i in range(100):
        img, meta = _make_receipt(i, fake)
        path = out_dir / f"r{i + 1:03d}.png"
        img.save(path, optimize=True)
        meta["filename"] = path.name
        truth.append(meta)

    truth_path = out_dir / "_ground_truth.json"
    truth_path.write_text(
        json.dumps(truth, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"✓ Generated 100 receipts → {out_dir}/")
    print(f"  Ground truth → {truth_path}")


if __name__ == "__main__":
    main()
