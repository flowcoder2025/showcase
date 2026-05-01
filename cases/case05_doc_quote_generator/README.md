# Case 05 — 견적서/거래명세서 자동 생성 (Word + PDF)

## 시나리오
이대리(영업)가 매번 견적서를 작성할 때 양식 복붙·표 그리기·합계 계산에 약 30분이 든다. 거래처마다 양식이 미묘하게 달라지고, 합계 오타·누락이 종종 발생한다.

이 케이스는 견적 요청 Excel 한 장을 입력으로 받아 **거래처별로 docx + pdf를 동시에 생성**한다 (한 견적당 5초 미만).

## 실행
```bash
# 권장: 안전 모드 — 외부 API 없음, 실제 docx/pdf 생성
DEMO_SAFE=1 uv run python runner.py case05_doc_quote_generator --safe

# 라이브 실행 (동일 — 본 케이스는 외부 API를 사용하지 않음)
uv run python runner.py case05_doc_quote_generator
```

### 입력 데이터
`personas/sample_data/quote_requests.xlsx` (기본 fallback). `vendors.xlsx` 30곳 중 10곳을 deterministic 샘플 (Faker seed=42).

```bash
uv run python personas/sample_data/quote_requests.py
```

### 입력 컬럼 (기본 스키마)
| 한글 컬럼 | 의미 | column_map 키 |
|---|---|---|
| 견적번호 | 견적 그룹 ID | `request_id` |
| 거래처명 | 거래처 이름 | `vendor` |
| 담당자 | 거래처 담당자 | (참조용, 본문 미사용) |
| 이메일 | 담당자 이메일 | (참조용) |
| 품목 | 품목명 | `name` |
| 수량 | 수량 (정수) | `qty` |
| 단가 | 단가 (정수) | `price` |
| 납기일 | 납기일 (YYYY-MM-DD) | `due_date` |

다른 컬럼 스키마(예: `request_no/customer/product/units/unit_price/delivery`)도 `column_map` override로 동일하게 처리 가능 — Phase 1에서 검증한 재사용성 패턴.

### 직접 모듈 실행
```bash
# runner의 safe_mode 인터셉트를 거치지 않으므로 본 케이스에선 동일 결과
uv run python -m cases.case05_doc_quote_generator.scenario
```

## 결과
- `output/{견적번호}.docx` — python-docx로 생성한 한글 폰트 명시 견적서
- `output/{견적번호}.md` — pdf 생성용 markdown (감사 추적용)
- `output/{견적번호}.pdf` — md-to-pdf 스킬(npx tsx) 호출 결과

`build_quote`가 자동으로 `sum(qty * price)`로 합계를 산정하므로 오타·누락 위험이 없다.

## 출력 파일 관리

`output/` 디렉토리에 생성되는 파일:
- `{견적번호}.docx` — Word 견적서 (시연·고객 발송용)
- `{견적번호}.md` — 중간 markdown (감사 추적용, 삭제 가능)
- `{견적번호}.pdf` — PDF 견적서 (시연·메일 첨부용)

md 파일은 pdf 생성 중간 산출물입니다. 시연 후 정리는 `rm output/*.md`.

## 시연 임팩트
- Before: 거래처 1곳당 양식 복붙·표 작성·합계 계산 약 30분
- After: 10건 일괄 처리도 30초 내, 모든 견적이 동일 양식 + 자동 합계
- ChatGPT 대비: 사내 양식 일관성 (회사 로고·폰트·표 스타일이 코드에 묶여 있음)

## 주의
- `output/`에는 거래처명·금액이 노출될 수 있으므로 시연 환경 외 공유 금지.
- 실제 시연 직전 `uv run python runner.py --check --strict`로 npx + md-to-pdf 스킬 가용성 확인 필요.
