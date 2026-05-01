"""미수금 시드 생성기 — vendors.xlsx 30곳 재사용.

분포 (deterministic, Faker seed=42):
- 0~14일  (friendly): 40% (~24건)
- 15~30일 (neutral):  30% (~18건)
- 31~60일 (strict):   20% (~12건)
- 60+일   (final):    10% (~6건)
- 총 약 60건 (거래처당 평균 2건)

실행:
    uv run python personas/sample_data/overdue_invoices.py
"""

import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from faker import Faker


def _pick_days(bucket: str) -> int:
    """bucket 별 연체일 샘플링."""
    if bucket == "friendly":
        return random.randint(0, 14)
    if bucket == "neutral":
        return random.randint(15, 30)
    if bucket == "strict":
        return random.randint(31, 60)
    # final
    return random.randint(61, 180)


def main() -> Path:
    Faker.seed(42)
    random.seed(42)

    out_dir = Path(__file__).parent
    vendors_path = out_dir / "vendors.xlsx"
    if not vendors_path.exists():
        raise FileNotFoundError(
            f"vendors.xlsx not found at {vendors_path} — "
            "run `uv run python personas/sample_data/generate.py` first"
        )

    vendors = pd.read_excel(vendors_path)

    # 거래처당 평균 2건 → 30 * 2 = 60건
    # bucket 분포: 24/18/12/6
    plan: list[str] = ["friendly"] * 24 + ["neutral"] * 18 + ["strict"] * 12 + ["final"] * 6
    random.shuffle(plan)

    # 납기일 = 시연 환경 today(2026-05-01) - 연체일로 역산해 연체일과 일치시킨다.
    today = datetime(2026, 5, 1)
    rows: list[dict[str, object]] = []
    for i, bucket in enumerate(plan):
        v = vendors.iloc[i % len(vendors)]
        days = _pick_days(bucket)
        due = today - timedelta(days=days)
        rows.append(
            {
                "거래처명": str(v["거래처명"]),
                "거래번호": f"OD-{i + 1:04d}",
                "금액": random.randint(300_000, 8_000_000),
                "납기일": due.strftime("%Y-%m-%d"),
                "연체일": days,
                "담당자": str(v["담당자"]),
            }
        )

    df = pd.DataFrame(rows)
    out_path = out_dir / "overdue_invoices.xlsx"
    df.to_excel(out_path, index=False)
    print(f"Generated: {out_path} ({len(df)} rows)")
    print(df["연체일"].describe())
    return out_path


if __name__ == "__main__":
    main()
