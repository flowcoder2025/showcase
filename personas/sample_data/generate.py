"""AX상사 가상 거래처·거래 데이터 생성 (Faker).

실행:
    uv run python personas/sample_data/generate.py
"""
import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from dateutil.relativedelta import relativedelta
from faker import Faker


def main() -> None:
    fake = Faker("ko_KR")
    Faker.seed(42)
    random.seed(42)

    out_dir = Path(__file__).parent
    vendors_dir = out_dir / "vendors"
    vendors_dir.mkdir(exist_ok=True)
    invoices_dir = out_dir / "invoices"
    invoices_dir.mkdir(exist_ok=True)

    # 거래처 30곳
    vendors = []
    for i in range(30):
        vendors.append({
            "vendor_id": f"V{i+1:03d}",
            "거래처명": fake.company(),
            "사업자번호": fake.unique.ssn().replace("-", "")[:10],
            "담당자": fake.name(),
            "이메일": fake.email(),
        })
    pd.DataFrame(vendors).to_excel(out_dir / "vendors.xlsx", index=False)

    # 12개월 거래 — 월별 파일
    base = datetime(2026, 1, 1)
    for month_offset in range(12):
        month_start = base + relativedelta(months=month_offset)
        rows = []
        for _ in range(random.randint(40, 80)):
            v = random.choice(vendors)
            rows.append({
                "거래처명": v["거래처명"],
                "거래일": month_start + timedelta(days=random.randint(0, 28)),
                "금액": random.randint(50_000, 5_000_000),
                "품목": fake.bs().split()[0],
            })
        df = pd.DataFrame(rows)
        df.to_excel(vendors_dir / f"transactions_{month_start:%Y_%m}.xlsx", index=False)

    # 거래명세서 100건 (단가·수량 — case02 검증용)
    invoices = []
    for i in range(100):
        v = random.choice(vendors)
        unit_price = random.randint(1_000, 100_000)
        qty = random.randint(1, 200)
        # 5% 확률로 의도적 이상치 (표준 단가의 3배 이상)
        if random.random() < 0.05:
            unit_price *= random.randint(3, 5)
        invoices.append({
            "거래명세서번호": f"INV-{i+1:04d}",
            "거래처명": v["거래처명"],
            "품목": fake.bs().split()[0],
            "단가": unit_price,
            "수량": qty,
            "금액": unit_price * qty,
        })
    pd.DataFrame(invoices).to_excel(invoices_dir / "invoices.xlsx", index=False)

    print("✓ Generated: vendors.xlsx (30), transactions_*.xlsx (12 months), invoices.xlsx (100)")


if __name__ == "__main__":
    main()
