"""case03용 견적 메일 발송 대상 시드 — 50건. vendors 30곳 + 신규 20곳 (Faker seed=42).

실행:
    uv run python personas/sample_data/quote_dispatch_list.py
"""

from __future__ import annotations

import random
from pathlib import Path

import pandas as pd
from faker import Faker


def main() -> None:
    fake = Faker("ko_KR")
    Faker.seed(42)
    random.seed(42)

    here = Path(__file__).parent
    vendors_df = pd.read_excel(here / "vendors.xlsx")

    rows: list[dict[str, object]] = []
    for _, vrow in vendors_df.iterrows():
        rows.append(
            {
                "거래처명": vrow["거래처명"],
                "담당자": vrow["담당자"],
                "이메일": vrow["이메일"],
                "견적번호": f"Q-2026-{len(rows) + 1:03d}",
                "품목요약": fake.bs().split()[0],
                "예상금액": random.randint(500_000, 50_000_000),
                "과거거래": random.choice(
                    [
                        "최근 6개월 거래 1건",
                        "장기 거래처 (3년+)",
                        "신규 거래 가능성 검토 중",
                        "이전 견적 수령 후 미체결",
                    ]
                ),
            }
        )

    # 추가 20건 — 신규 거래처
    for _ in range(20):
        rows.append(
            {
                "거래처명": fake.company(),
                "담당자": fake.name(),
                "이메일": fake.email(),
                "견적번호": f"Q-2026-{len(rows) + 1:03d}",
                "품목요약": fake.bs().split()[0],
                "예상금액": random.randint(500_000, 50_000_000),
                "과거거래": "신규 거래처 — 첫 견적",
            }
        )

    df = pd.DataFrame(rows)
    out_path = here / "quote_dispatch_list.xlsx"
    df.to_excel(out_path, index=False)
    print(f"✓ Generated {out_path.name} — {len(df)} rows")


if __name__ == "__main__":
    main()
