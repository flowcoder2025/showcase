# Case 03 시연 대본 — 견적 메일 일괄 발송 (이대리)

페르소나: 이대리(영업). 거래처 50곳에 분기별 견적 메일을 보내는데, 각자 본문이 미묘하게 달라야 하고 PDF 견적서를 1건씩 만들어 첨부해야 한다. 평소 1시간이 걸리는 작업.

## 1분 버전 (5건 시연)

### 컨텍스트 (10초)
"이대리가 매 분기 50곳에 견적 메일을 보냅니다. 본문에 담당자명·과거 거래 메모가 들어가고, PDF 견적서를 1건씩 만들어 첨부해야 해서 수작업 1시간."

### 실행 (40초)
```bash
DEMO_SAFE=1 uv run python runner.py case03_email_quote_dispatch --safe
```
- 콘솔: `[Q-2026-001] 거래처A → 담당자@회사 (safe-fallback)` 50줄이 흘러간다 (5건만 발췌해 강조).
- 결과 폴더에서 1건의 PDF 견적서 + 메일 미리보기 1건을 시연.

### 마무리 (10초)
"실제 라이브에서는 Gmail API / SMTP로 발송. 본문은 거래처별로 자동 개인화. 30초 안에 50건이 큐잉됩니다."

---

## 3분 버전 (50건 일괄)

### 1. Before (40초)
- 평소 메일: 같은 안내문 본문, 거래처별로 담당자명·과거 거래 메모만 다르게.
- 견적서 PDF: 양식 복붙 + 합계 계산 + PDF 변환 = 1건당 1분+.
- 50곳 × 1분 = **약 60분**, 그 중 **합계 오타·담당자명 실수**가 나오면 응대 메일까지 추가.

### 2. 자동화 시연 (90초)
```bash
DEMO_SAFE=1 uv run python runner.py case03_email_quote_dispatch --safe
```
- 입력: `personas/sample_data/quote_dispatch_list.xlsx` (50건, deterministic seed)
- 콘솔: `built 50 / sent 50 / errors 0` summary
- 출력 폴더: `Q-2026-001.pdf` ~ `Q-2026-050.pdf` 50건

### 3. 개인화 비교 (40초)
2건의 메일 본문을 펼쳐 보여주고:
- 거래처A: "장기 거래처 (3년+)" 메모 → 본문 마지막 줄에 등장
- 거래처B: "신규 거래처 — 첫 견적" 메모 → 본문 마지막 줄에 다른 톤으로 등장
- 견적번호·예상금액·품목요약은 모두 다름

### 4. 마무리 (10초)
"60분 → 30초. 거래처별 PDF + 개인화 메일이 한 번에 큐잉. 발송 성공/실패는 summary로 후처리."

---

## 5분 버전 (+ 차별화 + safe_mode)

위 3분 흐름 + 다음을 추가.

### 5. ChatGPT 대비 차별화 (40초)
- ChatGPT로 메일 본문은 만들 수 있지만:
  - 사내 표준 톤·맺음말 일관 적용 (코드에 묶여 있음)
  - 과거 거래 컨텍스트 자동 주입 (Excel의 `과거거래` 컬럼)
  - 견적 PDF 자동 첨부 (md-to-pdf 스킬)
  - 50건 발송 결과 summary로 사후 추적

### 6. safe_mode 시연 (40초)
- `DEMO_SAFE=1` 토글 → 외부 호출(Gmail API) 없이 동일 흐름.
- 실제 발송은 단일 patch point (`core.messaging.email.send`) 가 차단.
- 시연·교육·QA 환경에서 동일 코드 그대로 안전하게 반복 가능.

### 7. 라이브 발송 모드 (옵션, 30초)
- `runner.py --check --strict` 로 Gmail OAuth + Discord webhook ping 등 사전 검증.
- 실제 발송은 `GMAIL_OAUTH_CREDENTIALS` (Gmail API) 또는 `SMTP_HOST/USER/PASS` (SMTP) 환경변수 설정 후 동일 명령.

---

## 시연 체크리스트

- [ ] `personas/sample_data/quote_dispatch_list.xlsx` 50건 존재
- [ ] `output/` 비워둠 (`rm cases/case03_email_quote_dispatch/output/Q-*` — `.gitkeep` 보존)
- [ ] `npx tsx` PATH 확인 (md-to-pdf 스킬 호출용)
- [ ] (라이브) `GMAIL_SENDER` + `GMAIL_OAUTH_CREDENTIALS` 또는 SMTP 변수
- [ ] `runner.py --check --strict` 통과
