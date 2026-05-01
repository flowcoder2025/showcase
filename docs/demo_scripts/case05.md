# Case 05 — 시연 대본 (견적서/거래명세서 자동 생성)

페르소나: **이대리** (영업). 견적 1건당 양식 복붙·표·합계 계산 약 30분 → **5초**.

## 1분 버전 (고객 미팅 임팩트)

**[10초] 페인**
> "이대리님이 견적서 한 장 작성하실 때 양식 복붙하시고 표 그리시고 합계 계산 다시 확인하시면 30분 가까이 걸리시잖아요. 그것도 한 건일 때 얘기고요."

**[5초] 실행**
```bash
DEMO_SAFE=1 uv run python runner.py case05_doc_quote_generator --safe
```

**[30초] 결과**
- 콘솔: `docx 10건 / pdf 10건 / 실패 0건` (30초 내 완료)
- `output/Q-2026-001.docx` Quick Look으로 열기 → 한글 폰트 + 표 양식 확인
- 같은 폴더의 `Q-2026-001.pdf` 동시 열기 → 양쪽 동일 양식
- 표 마지막 행: **합 계: 자동 계산값** (오타·누락 위험 0)

**[15초] 임팩트**
> "10건을 30초에. 양식이 코드에 묶여 있어서 누가 돌려도 똑같이 나옵니다. ChatGPT는 매번 양식이 미묘하게 달라지지만 이건 영구 일관성입니다."

## 3분 버전

1분 버전 + 다음 항목 추가:

**[40초] 일괄성·확장성**
- 입력 엑셀 한 장 (`personas/sample_data/quote_requests.xlsx`) → 10 견적번호 × 평균 4-5 품목 = 42행
- 견적번호별 자동 그룹화 → 각 견적당 docx + pdf 1쌍
- 합계는 모든 행에 대해 `qty * price` 자동 합산. 사람이 손대지 않으니 오타가 원천 봉쇄

**[40초] PDF 생성 파이프라인**
- 동일 데이터로 markdown 별도 생성 → md-to-pdf 스킬(npx tsx) 호출 → PDF
- 거래처에는 PDF, 사내 보관은 docx — 같은 소스에서 두 포맷 동시 산출

**[40초] 페일소프트**
- 한 견적 처리 실패해도 다른 견적 계속 진행 (per-request error isolation)
- summary에 `errors`, 각 행에 `request_id`/`vendor`/`n_items` 기록 → 나중에 어떤 견적이 누락됐는지 즉시 추적

## 5분 버전

3분 버전 + 다음 항목 추가:

**[60초] column_map 재사용성**
- 기본 입력 컬럼: `견적번호 / 거래처명 / 품목 / 수량 / 단가 / 납기일`
- 다른 ERP에서 export한 입력은 컬럼이 다를 수 있음 (예: `request_no / customer / product / units / unit_price / delivery`)
- `column_map` 파라미터로 매핑만 바꾸면 코드 변경 없이 동일 시나리오 재사용
   ```python
   scenario.run(
       input_path=other_erp.xlsx,
       column_map={
           "request_id": "request_no",
           "vendor": "customer",
           "name": "product",
           "qty": "units",
           "price": "unit_price",
           "due_date": "delivery",
       },
   )
   ```
- 다음 컨설팅 프로젝트에서 `core/docgen/word.py`만 import해 자체 양식으로 재활용 가능

**[60초] ChatGPT 대비 차별화**
- ChatGPT: 매번 다른 표 양식, 합계 오류 종종 발생, 한글 폰트 깨짐
- 이 시스템: 양식·폰트·합계 로직이 코드에 묶여 있어 영구 일관성
- 회사 로고·CI·표 스타일 변경이 필요해도 `core/docgen/word.py` 한 곳만 수정

## 시연 환경 체크리스트

- [ ] `uv run python runner.py --check --strict` 통과 — npx + md-to-pdf 스킬 디렉토리 확인
- [ ] `personas/sample_data/quote_requests.xlsx` 존재 — 없으면 `uv run python personas/sample_data/quote_requests.py` 실행
- [ ] Apple SD Gothic Neo (또는 `AX_KOREAN_FONT`로 지정한 폰트) 시스템 설치 확인
- [ ] `output/` 비우기 — 이전 시연 결과가 자동 열기에 섞이지 않도록
