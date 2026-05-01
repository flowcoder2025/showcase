# Case 09 — 거래처 응대 메일 AI 초안

## 시나리오
이대리가 거래처 답신 한 통에 톤 고민 10분.
이 케이스는 사내 톤·과거 거래 이력을 컨텍스트로 주입해 차별화된 3안 생성.

## 실행
```bash
uv run python -m cases.case09_ai_email_drafter.scenario
DEMO_SAFE=1 uv run python -m cases.case09_ai_email_drafter.scenario  # 안전 모드
```
