# Case 03 — 견적 메일 일괄 발송 (개인화 + PDF 첨부)

## 시나리오
이대리(영업)가 거래처 50곳에 동일한 안내문에 거래처별로 다른 견적서를 첨부해 메일을 보낸다. 거래처마다 본문에 담당자명·과거 거래 메모를 다르게 넣어야 하고, PDF 견적서를 1건씩 만들어 첨부해야 해서 수작업으로는 약 60분이 걸린다.

이 케이스는 발송 대상 Excel 한 장을 입력으로 받아 **거래처별 PDF 견적서를 자동 생성하고, 개인화된 본문(텍스트 + HTML)에 첨부해 일괄 발송**한다.

## 실행
```bash
# 권장: 안전 모드 — 외부 발송 없음, PDF는 실제 생성
DEMO_SAFE=1 uv run python runner.py case03_email_quote_dispatch --safe

# 라이브 실행 (Gmail OAuth 또는 SMTP 환경변수 필요 — 아래 참조)
uv run python runner.py case03_email_quote_dispatch
```

### 입력 데이터
`personas/sample_data/quote_dispatch_list.xlsx` (기본 fallback). `vendors.xlsx` 30곳 + Faker로 추가 20곳 (Faker seed=42). 합계 50건 deterministic.

```bash
uv run python personas/sample_data/quote_dispatch_list.py
```

### 입력 컬럼 (기본 스키마)
| 한글 컬럼 | 의미 | column_map 키 |
|---|---|---|
| 거래처명 | 거래처 이름 | `vendor` |
| 담당자 | 담당자 이름 | `contact` |
| 이메일 | 수신자 주소 | `to` |
| 견적번호 | 견적 식별자 | `quote_no` |
| 품목요약 | 본문 안내용 1줄 | `summary` |
| 예상금액 | 정수(원) | `amount` |
| 과거거래 | 본문 footer 메모 | `history` |

다른 컬럼 스키마도 `column_map` override로 동일하게 처리 가능 (Phase 1에서 검증한 재사용성 패턴).

### 직접 모듈 실행
```bash
DEMO_SAFE=1 uv run python -m cases.case03_email_quote_dispatch.scenario
```

## Gmail OAuth / SMTP 사전 셋업 (라이브 발송용)

라이브 발송은 `core.messaging.email.send` 가 다음 우선순위로 transport를 선택한다.

1. `GMAIL_OAUTH_CREDENTIALS` 환경변수 + 파일 존재 → Gmail API
2. `SMTP_HOST` + `SMTP_USER` + `SMTP_PASS` 모두 설정 → SMTP STARTTLS
3. 둘 다 없음 → `force_safe()` 자동 폴백 (외부 호출 안 함)

발신자(`From`)는 `GMAIL_SENDER` 환경변수 필수.

자세한 설정 절차는 `core/messaging/email.py` 참조.

## 결과
- `output/{견적번호}.md` — pdf 생성용 markdown (감사 추적용)
- `output/{견적번호}.pdf` — md-to-pdf 스킬(npx tsx) 호출 결과 (메일 첨부)
- 콘솔: `[Q-2026-NNN] {거래처명} → {이메일} (transport)` per-request 로그
- summary dict: `built / sent / errors / transports / rows`

`built` 는 `build_message` 성공 건수, `sent` 는 실제 발송(또는 safe-fallback) 건수, `errors` 는 빌드/발송 실패 건수다. **PDF 생성 실패는 errors가 아니다** — 첨부만 누락한 채 메일 발송은 그대로 진행된다 (per-row 격리).

## 시연 임팩트
- Before: 50곳 1시간 (개인화 + PDF 첨부)
- After: 30초 (`DEMO_SAFE=1` 시연 시 PDF만 실제 생성, 발송은 safe-fallback)
- ChatGPT 대비: 사내 톤 + 과거 거래 컨텍스트 자동 주입 + 견적 PDF 일관성

## 보안 / 주의
- HTML 본문은 `email.build_html_body` (autoescape) 경유로 빌드 — 거래처명에 `<script>` 등 포함되어도 escape 처리됨 (T7a.5 XSS 방어).
- `output/`에는 거래처명·금액이 노출되므로 시연 환경 외 공유 금지.
- 시연 직전 `uv run python runner.py --check --strict` 로 npx + md-to-pdf 스킬 + (라이브 시) Gmail/SMTP 환경변수 확인.
