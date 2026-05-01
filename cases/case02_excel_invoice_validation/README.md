# Case 02 — 거래명세서 단가 검증 + Discord 이상치 알림

## 시나리오
최주임이 매일 거래명세서 100건의 단가·수량을 수기 대조 — 1~2시간.
이 케이스는 품목별 단가 표준편차 기반 이상치를 자동 검출하고 Discord 채널에 알림.

## 실행
```bash
# 권장: runner를 통한 실행 (안전 모드, 외부 API 미호출)
uv run python runner.py case02_excel_invoice_validation --safe

# 라이브 실행 (실제 Discord webhook 호출)
uv run python runner.py case02_excel_invoice_validation
```

### 직접 모듈 실행 (라이브 환경 전용)
```bash
# 시나리오를 모듈로 직접 실행하면 runner의 safe_mode 인터셉트를 거치지 않으므로
# 반드시 DISCORD_WEBHOOK_URL이 설정되어 있어야 한다.
uv run python -m cases.case02_excel_invoice_validation.scenario
```
runner.py가 유일한 intercept boundary이므로, 안전 모드 시연은 항상 runner 경유로 실행한다.

## 시연 임팩트
- Before: 1~2시간 수기 대조
- After: 10초 + Discord 자동 통보
