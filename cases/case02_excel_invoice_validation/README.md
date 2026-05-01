# Case 02 — 거래명세서 단가 검증 + Discord 이상치 알림

## 시나리오
최주임이 매일 거래명세서 100건의 단가·수량을 수기 대조 — 1~2시간.
이 케이스는 품목별 단가 표준편차 기반 이상치를 자동 검출하고 Discord 채널에 알림.

## 실행
```bash
uv run python -m cases.case02_excel_invoice_validation.scenario
# 안전 모드(외부 API 미호출)
DEMO_SAFE=1 uv run python -m cases.case02_excel_invoice_validation.scenario
```

## 시연 임팩트
- Before: 1~2시간 수기 대조
- After: 10초 + Discord 자동 통보
