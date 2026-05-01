"""case05용 견적 요청 시드 — 10건. vendors.xlsx 재사용 + Faker seed=42.

실행:
    uv run python personas/sample_data/quote_requests.py
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
    sample = vendors_df.sample(n=10, random_state=42).reset_index(drop=True)

    rows: list[dict[str, object]] = []
    for idx, (_, vrow) in enumerate(sample.iterrows()):
        n_items = random.randint(3, 7)
        request_id = f"Q-2026-{idx + 1:03d}"
        for _ in range(n_items):
            rows.append(
                {
                    "견적번호": request_id,
                    "거래처명": vrow["거래처명"],
                    "담당자": vrow["담당자"],
                    "이메일": vrow["이메일"],
                    "품목": fake.bs().split()[0],
                    "수량": random.randint(1, 100),
                    "단가": random.randint(10_000, 500_000),
                    "납기일": "2026-06-30",
                }
            )

    df = pd.DataFrame(rows)
    out_path = here / "quote_requests.xlsx"
    df.to_excel(out_path, index=False)
    print(f"✓ Generated {out_path.name} — {len(df)} rows ({df['견적번호'].nunique()} requests)")


if __name__ == "__main__":
    main()
