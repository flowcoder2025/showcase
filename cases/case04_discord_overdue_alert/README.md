# Case 04 — 미수금 단계별 Discord 알림

## 시나리오
박과장이 매주 미수금 회수 체크·거래처 연락에 약 2시간을 쓴다. 연체일에 따라 톤이 달라야 하는데(친근 → 중립 → 단호 → 법무 escalation), 일일이 작성하면 누락·일관성 문제가 생긴다.

이 케이스는 미수금 데이터를 읽어 **연체일 4단계 분기**로 Discord 사내 채널(NDA-safe)에 자동 알림을 보낸다.

| 연체일 | level | 임베드 색상 | 톤 |
|---|---|---|---|
| 0~14일 | friendly | 파랑 (info) | 안부 + 확인 부탁 |
| 15~30일 | neutral | 주황 (warning) | 정중 독촉 |
| 31~60일 | strict | 빨강 (danger) | 단호 |
| 60+일 | final | 검정 (critical) | 법무팀 escalation 통지 |

## 실행
```bash
# 권장: runner를 통한 안전 모드 실행 (외부 webhook 호출 없음)
DEMO_SAFE=1 uv run python runner.py case04_discord_overdue_alert --safe

# 라이브 실행 (실제 Discord 사내 채널로 발송)
uv run python runner.py case04_discord_overdue_alert
```

### 입력 데이터
`personas/sample_data/overdue_invoices.xlsx` (기본 fallback) — `personas/sample_data/overdue_invoices.py`로 생성한다.

```bash
uv run python personas/sample_data/overdue_invoices.py
```

`vendors.xlsx`의 30곳을 재사용해 거래처당 평균 2건, 총 60건의 deterministic 시드 (Faker seed=42).

### 직접 모듈 실행 (라이브 환경 전용)
```bash
# runner의 safe_mode 인터셉트를 거치지 않으므로 DISCORD_WEBHOOK_URL 필수.
uv run python -m cases.case04_discord_overdue_alert.scenario
```

## 시연 임팩트
- Before: 매주 2시간 수기 회수 체크·연락
- After: **8초**, 단계별 톤 자동 분기 + Discord 임베드 색상 차이로 시각 구분

## NDA·보안 주의
- **사내 NDA 채널** 한정 발송 (거래처명·금액 노출 가능). 공개 채널 webhook 사용 금지.
- 카카오 자동발송은 약관·스팸법으로 금지 — Discord 사내 알림으로 대체.
- 시연 시 webhook URL은 secrets/discord_test.txt 또는 env (`DISCORD_WEBHOOK_URL`)로만 주입.
