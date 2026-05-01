# 60분 강의 흐름 — 사무자동화 컨설팅 라이브 시연

> **대상**: 중소기업 대표·관리자급 청중 (제조·유통 업종 가정).
> **목적**: AX 컨설팅의 가치제안과 10개 자동화 케이스를 한 호흡에 시연.
> **선결 조건**: `uv run python runner.py --check --strict` 통과, Ollama warmup, Discord webhook 등록, OpenRouter 키, Gmail OAuth (case03 라이브 시), 한글 GUI (case06 결과 확인용).
> **HEAD 기준**: `ecf70a6` (Phase 2 T18 case06 완료, T19 강의 노트).

---

## 목차 (시간 마커)

| 시간 | 블록 | 내용 |
|---|---|---|
| 0:00 - 0:05 | 인트로 | 왜 사무자동화인가, AX상사 페르소나, 카테고리 5개 소개 |
| 0:05 - 0:10 | Excel 1 | case01 — 거래처별 월별 매출 보고서 (박과장) |
| 0:10 - 0:15 | Excel 2 | case02 — 단가 검증 + Discord 이상치 알림 (최주임) |
| 0:15 - 0:20 | Messaging 1 | case04 — 미수금 단계별 Discord 알림 (박과장) |
| 0:20 - 0:25 | Messaging 2 | case03 — 견적 메일 일괄 발송 + PDF 첨부 (이대리) |
| 0:25 - 0:30 | Docgen 1 | case05 — 견적서 Word/PDF 자동 생성 (이대리) |
| 0:30 - 0:35 | Docgen 2 | case06 — 정부지원사업 HWPX 자동 작성 (김사장) |
| 0:35 - 0:40 | OCR 1 | case07 — 영수증 100장 OCR (Gemma 4 E2B, 박과장) |
| 0:40 - 0:45 | OCR 2 | case08 — 세금계산서 OCR + 회계 CSV (Gemma 4 E4B, 박과장) |
| 0:45 - 0:50 | AI 1 | case09 — 거래처 응대 메일 AI 초안 3안 (이대리) |
| 0:50 - 0:55 | AI 2 | case10 — 회의록 텍스트 → 요약·액션 (김사장) |
| 0:55 - 1:00 | Q&A | 자주 받는 질문 + 다음 단계 워크숍 안내 |

---

## [0:00 - 0:05] 인트로 — 사무자동화 컨설팅이 무엇을 자동화하는가

### 1. 첫 한 마디 (30초)

> "오늘 60분 동안 10개 사례를 직접 돌려 보여드릴 겁니다. 다 가상의 회사 'AX상사'에서 일하시는 네 분이 매일 하시는 진짜 업무입니다. 한 케이스도 시간 때우기로 만들지 않았어요. 끝나고 나서 '이건 우리 회사도 똑같다'는 케이스가 최소 두세 개는 잡히실 겁니다."

(강사 노트: 청중 반응 살피기. 고개 끄덕임 1~2번 보이면 다음 슬라이드로.)

### 2. 왜 사무자동화인가 — 시간 비교 (90초)

오늘 시연할 10개 케이스를 합산하면:

| 항목 | 합계 | 비고 |
|---|---|---|
| 수기 작업 (manual) | **약 970분 (16시간)** | 매월/매주 반복 (각 case meta.yaml 합산) |
| 자동화 (automated) | **약 456초 (7분 36초)** | 전체 케이스 합계 (각 케이스 시연 길이) |

> "월 16시간이 7분으로 줄어듭니다. 직원 한 명의 한 달 야근 5일이 사라지는 셈입니다. 그리고 야근만 없어지는 게 아니라 **사람 손에서 나오는 오타**가 같이 사라집니다 — 사업자번호 한 자리, 합계 한 줄."

(강사 노트: 오타 손해 사례 한 줄 즉흥 추가 가능 — "부가세 신고 후에 알아채면 재신고가 반나절 더".)

### 3. 카테고리 5개 (90초)

오늘 시연 케이스는 5개 카테고리로 묶입니다.

1. **Excel** — 합치기, 피벗, 검증 (case01, case02)
2. **Messaging** — 메일 일괄 발송, Discord 알림 (case03, case04)
3. **Docgen** — Word·PDF·HWPX 양식 자동 생성 (case05, case06)
4. **OCR** — 영수증·세금계산서 이미지 → 표 (case07, case08)
5. **AI** — 메일 초안, 회의록 요약 (case09, case10)

> "어떤 카테고리에 자기 회사 업무가 매핑되는지 봐주세요. 끝나고 1:1 워크숍에서 그 케이스부터 적용 시뮬레이션 합니다."

### 4. AX상사 페르소나 (60초)

가상의 회사 **AX상사** — 직원 35명, 제조·유통 겸업, 연 매출 70~90억. ERP는 1990년대 초기 도입에 엑셀+카톡+Gmail 의존. 오늘 시연의 주인공은 네 명입니다.

| 인물 | 역할 | 오늘 등장 케이스 |
|---|---|---|
| **김사장** (50대, 대표) | 의사결정·미팅·회의 | case06 정부지원사업, case10 회의록 |
| **박과장** (40대, 관리/회계) | 매출 정리·미수금·영수증 | case01 매출, case04 미수금, case07 영수증, case08 세금계산서 |
| **이대리** (30대, 영업) | 견적·메일 | case03 견적 메일, case05 견적서, case09 응대 메일 |
| **최주임** (20대, 생산관리) | 거래명세서 처리 | case02 단가 검증 |

> "이분들 페인 포인트가 청중 회사의 페인 포인트입니다. 직급이 좀 다를 뿐."

(강사 노트: "지금 우리 회사 박과장 떠오르시죠?" 한마디로 청중 끌어들이기.)

### 5. 시연 흐름 약속 (30초)

각 케이스마다 **Before (1분) → Demo (2~3분) → After (1~2분)** 순서로 진행합니다.

- **Before**: 수기 작업의 고통점
- **Demo**: 실제 코드 실행 + 결과 확인
- **After**: 자동화 효과 + 청중이 import해 쓸 수 있는 핵심 모듈

(강사 노트: 데모 실패 시 fallback — `DEMO_SAFE=1` 환경변수 토글하면 외부 API 안 호출하고도 동일 흐름 시연 가능. 시연 환경에서 Wi-Fi 끊겨도 멈추지 않음.)

### 6. 강의 약속 — 정직성 (R3-H1) (30초)

오늘 시연 데이터는 전부 **합성 데이터**입니다. 실제 거래처·사업자번호·금액이 아닙니다.

- 영수증 100장 (case07): Pillow 합성 + 노이즈/회전/블러 적용
- 세금계산서 30장 (case08): Pillow 합성 + 사업자번호도 알고리즘으로 체크섬 충족하는 임의값
- 회의록 5건 (case10): AX상사 페르소나 기반 시나리오 작성
- 견적·미수금 데이터: Faker + deterministic seed

> "그래서 '실제 환경에서도 똑같이 작동하는가'는 별도 검증 단계가 필요합니다. 도입 전 **사용 환경 데이터 5~10건 hold-out 검증**을 권장합니다. 시연이 잘된다고 도입이 잘되는 거 아닙니다 — 그 부분 정직하게 말씀드리고 시작합니다."

(강사 노트: 이 한 마디로 청중 신뢰 확보. "다 잘된다"고 호언하는 발표보다 "이런 한계 있다"고 인정하는 발표가 컨설팅 계약 더 잘 따냅니다.)

---

## [전환] Excel 블록 — "엑셀이 사무의 절반"

> "이제 첫 두 케이스 들어갑니다. 카테고리는 **Excel** 입니다. 중소기업 사무 업무의 절반은 엑셀이라고 봐도 무리가 없죠. 그 엑셀을 어디서 어떻게 자동화하느냐 — 박과장님이 매월 하시는 매출 보고서, 최주임님이 매일 하시는 단가 검증 두 케이스로 보여드립니다."

---

## [0:05 - 0:10] Excel 블록 1 — case01 거래처별 월별 매출 보고서

> 페르소나: **박과장** · 매월 거래처 30곳 엑셀 합치고 피벗 — **3시간 → 5초**

### Before (1분)

> "박과장님이 매월 1일 직전이 되면 거래처 30곳에서 엑셀 파일을 받습니다. 컬럼명이 회사마다 미묘하게 다르고요 — 어떤 회사는 '거래처명', 어떤 회사는 '고객사', 어떤 회사는 'Customer'. 30개를 손으로 합치고 거래처×월 피벗 만들고 차트 붙이는 데 **3시간**. 마감 다가올수록 야근 단골이죠."

(강사 노트: "매출 보고서 늦으면 김사장님이 답답하다고 하셨죠?" 인트로 페르소나와 연결)

### Demo (2~3분)

```bash
uv run python -m cases.case01_excel_vendor_report.scenario
```

콘솔 출력:
```
거래처별 월별 매출 보고서: before 180m → after 5s (~2160배)
```

- 자동으로 Quick Look 열림 → 거래처별 월별 매출표 + 막대 차트 한 시트.
- 입력 폴더 보여주기: `personas/sample_data/vendors/` — 12개월 파일 12개.
- 코드 한 화면 (`cases/case01_excel_vendor_report/scenario.py`) — 실제 호출은 3줄.

### After + Architecture (1~2분)

- **시간 효과**: 3시간 → 5초 (약 2,160배).
- **사용 모듈**:
  - `core/excel/reader.py` — 다중 파일 읽기 + `column_map` 매핑
  - `core/excel/merger.py` — 거래처/월 기준 합치기
  - `core/excel/pivot.py` — 피벗 + 합계 행
  - `core/excel/writer.py` — xlsx + 차트
- **재사용성**: 다른 회사에 적용할 때 `column_map`만 갈아끼우면 같은 시나리오 그대로. 코드 변경 0줄.

> "이 모듈은 다음 프로젝트에 가도 컬럼명 매핑만 바꾸면 그대로 돌아갑니다. 한 번 만들면 평생 자산입니다."

#### 핵심 설계 결정 — column_map 강제

기존 자동화 도구의 흔한 실패 패턴: "우리 회사 컬럼명에 맞춰 코드 짰는데 옆 회사 가니까 컬럼이 다 달라서 다시 짜야 함."

이 프로젝트는 그래서 엑셀 모듈에 **column_map 인자를 필수**로 강제합니다. 하드코딩 금지.

```python
# 이런 식으로 호출:
reader.read_vendors(
    folder="vendors/",
    column_map={
        "vendor": "거래처명",   # 또는 "고객사", "Customer"
        "amount": "매출액",     # 또는 "금액", "Sales"
        "date": "거래일자",     # 또는 "일자", "Date"
    },
)
```

> "다른 회사 가셔도 매핑만 바꾸시면 됩니다. 이 컨벤션이 컨설팅 자산을 평생 자산으로 만들어줍니다."

#### 청중 예상 질문

- **Q: "이게 매크로랑 뭐가 달라요?"**
  - A: 매크로는 한 회사 한 PC에 묶입니다. 이건 모듈 import만 하면 다른 프로젝트·다른 PC·다른 OS에서도 같이 돌아갑니다. 그리고 매크로는 디버깅·테스트 어렵죠. 이건 unit test가 통과해야 시연 무대에 올라옵니다.
- **Q: "엑셀 파일 100MB 넘으면?"**
  - A: pandas가 메모리에 통째로 올리니까 그 부분은 별도 스트리밍 처리 필요. 일반 중소기업 매출 데이터는 12개월치 합쳐도 수십 MB 안짝이라 문제 없습니다.
- **Q: "차트 모양 바꾸고 싶으면?"**
  - A: `core/excel/writer.py` 한 곳만 수정. openpyxl chart object 직접 만지시면 됩니다.

---

## [0:10 - 0:15] Excel 블록 2 — case02 단가 검증 + Discord 알림

> 페르소나: **최주임** · 거래명세서 100건 단가·수량 수기 대조 — **1~2시간 → 10초**

### Before (1분)

> "최주임님이 매일 거래명세서 100건의 단가·수량을 수기로 대조하시는데 1~2시간. 가끔 이상한 단가 한 건 놓치면 그게 그대로 손실로 직결됩니다. 100건 다 보긴 어렵잖아요."

### Demo (2~3분)

```bash
uv run python -m cases.case02_excel_invoice_validation.scenario
```

- 콘솔: `이상치 5건 검출` (10초 안에 완료)
- Discord 채널 화면 전환 → 알림 도착 ("거래명세서 단가 이상치 알림")
- Quick Look으로 outliers.xlsx 열기 — 단가 컬럼 강조

(강사 노트: Discord 화면을 미리 다른 모니터에 띄워 둠. 알림 들어오는 순간 청중 시선이 자연스럽게 이동.)

### After + Architecture (1~2분)

- **시간 효과**: 1~2시간 → 10초.
- **알고리즘**: 품목 그룹별 **leave-one-out z-score** (boundary outlier 누락 방지). 단순 평균/표준편차로 하면 outlier 자체가 std를 부풀려 놓치는 케이스가 있어 그렇게 안 함.
- **사용 모듈**:
  - `core/excel/validator.py` — `detect_unit_price_outliers` (LOO z-score)
  - `core/messaging/discord.py` — webhook 단일 patch point
  - `core/common/secrets_mask.py` — webhook URL 자동 마스킹

> "사람이 100건을 다 보지 않아도 됩니다. 의심되는 것만 즉시 채널로 갑니다. 그리고 이 패턴 — 그룹별 통계 이상치 — 은 재고·근태에도 그대로 적용됩니다."

#### 알고리즘 deep-dive — leave-one-out z-score

순진한 z-score는 outlier가 자기 자신을 포함한 평균·std에 영향을 미칩니다. 그래서 boundary outlier는 z-score가 낮게 나와 **놓치는 경우**가 발생합니다.

```python
# 순진한 z-score (놓치는 케이스)
z = (x - group.mean()) / group.std()

# Leave-one-out z-score (이 프로젝트 채택)
z = (x - group.drop(x).mean()) / group.drop(x).std()
```

> "이게 이 프로젝트의 verbatim 알고리즘은 아니었습니다. 처음엔 순진한 z-score로 짰는데, 테스트에서 boundary outlier 한 건이 빠지는 걸 발견하고 LOO로 바꿨습니다. T14.5 fixer commit에 기록되어 있습니다."

#### 청중 예상 질문

- **Q: "단가 마스터를 따로 안 두나요?"**
  - A: 마스터를 두면 좋은데, 중소기업은 마스터 자체가 정확하지 않은 경우가 많습니다. 그래서 마스터 없이 그룹별 통계로 fallback. 마스터 있으시면 그 자리에 마스터 검증 추가는 한 줄.
- **Q: "Discord 알림이 너무 많이 오면?"**
  - A: 임계값(threshold) 조정. 기본 ±2σ인데 ±3σ로 올리시면 진짜 심각한 것만 옵니다. 시연 후 워크숍에서 청중 회사 기준에 맞춰 튜닝.
- **Q: "카카오톡으로는 안 되나요?"**
  - A: 카카오톡 자동발송은 약관·스팸법 리스크. 대체로 **Discord 사내 NDA 채널**이 가장 안전. 외부 거래처에 직접 가는 건 case03 메일 발송이 그 역할.

---

## [전환] Messaging 블록 — "사람의 손에서 나가야 하는 메시지를 안전하게"

> "Excel은 사내 데이터 가공이었다면 Messaging은 외부 발신입니다. 발신은 잘못되면 사고가 큰 영역이죠 — 잘못 갔거나 안 갔거나. 두 개 케이스로 보여드립니다. case04는 사내 채널 알림 (안전), case03은 거래처 메일 일괄 발송 (PDF 첨부)."

---

## [0:15 - 0:20] Messaging 블록 1 — case04 미수금 단계별 Discord 알림

> 페르소나: **박과장** · 매주 미수금 회수 체크·연락 — **2시간 → 8초**

### Before (1분)

> "박과장님이 매주 미수금 거래처에 단계별로 다른 톤으로 연락하시잖아요. 친근 → 정중 → 단호 → 법무. 일일이 작성하다 보면 누락도 생기고, 톤 일관성도 깨집니다. 한 명이 너무 강하게 말해서 거래처와 관계가 안 좋아지기도 하고요."

### Demo (2~3분)

```bash
DEMO_SAFE=1 uv run python runner.py case04_discord_overdue_alert --safe
```

콘솔: `전송 60건 / 실패 0건` (8초 내 완료)

Discord 채널 화면 전환:
- 🔵 friendly 24건 (안부 + 확인)
- 🟠 neutral 18건 (정중 독촉)
- 🔴 strict 12건 (단호)
- ⚫ final 6건 (법무 escalation 통지)

> 임베드 색상이 한눈에 단계 구분.

(강사 노트: 한 단계씩 클릭해서 메시지 본문 보여주기. "톤이 정말 다르죠?")

### After + Architecture (1~2분)

- **시간 효과**: 2시간 → 8초.
- **단계 분기**: `classify_level(days)` — 0~14, 15~30, 31~60, 60+. boundary 한 변수로 정의되어 있어 회사 정책 다르면 그 한 줄만 수정.
- **카카오톡 자동발송 금지**: 약관·스팸법 리스크 회피. **사내 NDA Discord 채널만** 사용. 거래처 외부에 정보 안 나감.
- **사용 모듈**:
  - `core/messaging/discord.py::send_with_level` — 단계별 임베드 색상·아이콘
  - `core/excel/reader.py` — 미수금 엑셀 입력 (column_map)

> "60건을 8초에. 단계 톤은 코드에 묶여 있으니 누가 돌려도 일관됩니다. 그리고 이 패턴은 SLA 위반 알림, 재고 부족, 근태 결근 누적에도 동일 적용됩니다 — 도메인만 바꾸면 됩니다."

#### 단일 patch point 아키텍처 강조

`core/messaging/discord.py::send`만 가로채면 라이브 모드 ↔ safe 모드 전환이 무료입니다. `send_with_level`은 그 위 레이어. 이게 시연 환경 안정성의 비밀입니다.

```python
# runner.py가 단 한 곳만 patch
with safe_mode.intercept():
    # 시나리오 안에서 어떤 함수가 호출되든
    # discord.send만 차단하면 외부 발송 차단 완료
    case04.run(...)
```

> "단일 patch point 원칙. 시나리오·케이스 코드는 self-wrap 안 합니다. runner.py만 사실상 외부 호출 경계입니다. 이 원칙 깨면 시연 머신 어디선가 진짜 메시지가 외부로 발송될 수 있습니다."

#### 청중 예상 질문

- **Q: "Slack은 안 됩니까?"**
  - A: Slack 워크스페이스 webhook도 Discord와 같은 패턴. `core/messaging/slack.py` 추가만 하시면 됩니다. 본 시연은 Discord 하나로 통일.
- **Q: "거래처에 직접 가는 알림은?"**
  - A: 거래처 직접 발송은 case03 메일이 담당. Discord는 **사내 NDA 채널만**. 거래처 외부 노출 0건.
- **Q: "단계 정의 (0~14, 15~30, 31~60, 60+) 바꿀 수 있나요?"**
  - A: `classify_level(days)` 함수 한 줄. 회사 정책 다르면 거기서 boundary 한 변수만 수정.

---

## [0:20 - 0:25] Messaging 블록 2 — case03 견적 메일 일괄 발송 + PDF 첨부

> 페르소나: **이대리** · 거래처 50곳 분기 견적 메일 — **1시간 → 30초**

### Before (1분)

> "이대리님이 매 분기 거래처 50곳에 견적 메일을 보냅니다. 본문에 담당자명·과거 거래 메모가 들어가야 하고, PDF 견적서를 1건씩 만들어 첨부해야 해서 수작업 1시간. 합계 오타 한 번 나면 응대 메일까지 추가로 들어갑니다."

### Demo (2~3분)

```bash
DEMO_SAFE=1 uv run python runner.py case03_email_quote_dispatch --safe
```

- 콘솔: `built 50 / sent 50 / errors 0` summary
- 출력 폴더: `Q-2026-001.pdf` ~ `Q-2026-050.pdf` 50건
- 메일 본문 2건 비교:
  - 거래처A: "장기 거래처 (3년+)" 메모 → 본문 마지막 줄
  - 거래처B: "신규 거래처 — 첫 견적" 메모 → 다른 톤
- 견적번호·예상금액·품목요약은 모두 다름

(강사 노트: 라이브 발송 모드 시연 시 `GMAIL_SENDER` + `GMAIL_OAUTH_CREDENTIALS` 환경변수 필요. SMTP fallback 가능.)

### After + Architecture (1~2분)

- **시간 효과**: 60분 → 30초.
- **트랜스포트**: **Gmail API + SMTP 폴백** (환경 둘 중 하나만 갖춰져도 동작).
- **개인화**: Excel `과거거래` 컬럼 → 본문 마지막 줄 자동 주입 (Jinja2 템플릿 + XSS escape 적용).
- **PDF 첨부**: md-to-pdf 스킬 (`npx tsx scripts/md-to-pdf.ts`) — 한글 폰트 정상 렌더링.
- **사용 모듈**:
  - `core/messaging/email.py` — `build_message` (multipart + 첨부) + `send` (Gmail API/SMTP)
  - `core/docgen/pdf.py` — `md_to_pdf`
  - `core/common/secrets_mask.py` — Gmail/SMTP 자격증명 자동 마스킹

> "ChatGPT로 메일 본문은 만들 수 있지만, 사내 표준 톤·과거 거래 컨텍스트·PDF 자동 첨부·발송 결과 summary는 코드에 묶여 있어야 일관됩니다."

#### Gmail API + SMTP 폴백 — 왜 두 개를 다 지원하는가

회사 IT 환경이 다양합니다.

- **Gmail API (OAuth)**: 보안 정책상 SMTP 비밀번호 사용 금지인 회사 (대기업·금융권)
- **SMTP**: 자체 메일 서버 운영하는 회사 (제조·중견기업)

이 프로젝트는 둘 중 어떤 환경이든 동일한 코드로 발송:

```python
core.messaging.email.send(
    to="vendor@example.com",
    subject="...",
    body=...,
    attachments=[Path("Q-2026-001.pdf")],
)
# 내부적으로 GMAIL_OAUTH_CREDENTIALS 있으면 Gmail API
# 없으면 SMTP_HOST/USER/PASS로 폴백
```

> "환경변수 세팅만 다르고 시나리오 코드는 같습니다. 도입 환경 바뀌어도 코드 수정 0줄."

#### XSS 방어 — Jinja2 escape

거래처 메모에 HTML 태그가 들어가면 안 됩니다 (이메일 클라이언트가 렌더링하면 메일 깨짐 + 보안 취약).

```python
# core/docgen/template.py
template.render_html_string(template_str, **context)  # autoescape=True
```

> "거래처 메모를 사용자가 직접 입력하잖아요. 거기 `<script>` 같은 거 들어가면 안 되니까 Jinja2 autoescape 강제."

#### 청중 예상 질문

- **Q: "스팸 분류 안 되나요?"**
  - A: Gmail은 자기 도메인에서 자기 도메인으로 보내면 스팸 분류 거의 안 됩니다. SMTP는 SPF/DKIM 설정 필요. 도입 시 그 부분 같이 셋업.
- **Q: "수신자가 답장하면?"**
  - A: 답장은 case09가 담당. AI 메일 초안 생성 → 이대리 검토 → 발송.
- **Q: "발송 실패 50건 중 5건이면?"**
  - A: summary에 errors[] 목록. 실패 건만 따로 재시도 가능. 전체 재발송으로 중복 메일 가는 사고 방지.

---

## [전환] Docgen 블록 — "양식이 코드에 묶여 있어야 영구 일관성"

> "Messaging이 외부로 나가는 메시지였다면 Docgen은 외부로 나가는 문서입니다. 견적서·거래명세서·정부 신청서. 양식 통일성이 회사 신뢰도를 결정합니다."

---

## [0:25 - 0:30] Docgen 블록 1 — case05 견적서 Word/PDF 자동 생성

> 페르소나: **이대리** · 견적서 한 건 양식 복붙·표·합계 — **30분 → 5초**

### Before (1분)

> "이대리님이 견적서 한 장 작성하실 때 양식 복붙하시고 표 그리시고 합계 계산 다시 확인하시면 30분. 한 건일 때 얘기고요. 분기 50건이면…."

### Demo (2~3분)

```bash
DEMO_SAFE=1 uv run python runner.py case05_doc_quote_generator --safe
```

- 콘솔: `docx 10건 / pdf 10건 / 실패 0건`
- `output/Q-2026-001.docx` Quick Look — 한글 폰트 + 표 양식 확인
- 같은 폴더 `Q-2026-001.pdf` — 양쪽 동일 양식
- 표 마지막 행: **합 계: 자동 계산값** (오타 0)

### After + Architecture (1~2분)

- **시간 효과**: 30분 → 5초 (한 건 기준), 10건 30초.
- **이중 출력**: 사내 보관 docx + 거래처 발송용 pdf 동시 산출 (같은 소스).
- **페일소프트**: 한 견적 처리 실패해도 다른 견적 계속 진행 (per-request error isolation).
- **사용 모듈**:
  - `core/docgen/template.py` — Jinja2 (XSS 방어 `render_html_string`)
  - `core/docgen/word.py::build_quote` — 한글 폰트 명시 (Apple SD Gothic Neo, `AX_KOREAN_FONT` override)
  - `core/docgen/pdf.py::md_to_pdf` — npx tsx 호출 + `MdToPdfError`

> "양식이 코드에 묶여 있어 누가 돌려도 똑같이 나옵니다. 회사 로고·CI 변경되면 `core/docgen/word.py` 한 곳만 수정. 영구 일관성입니다."

#### 한글 폰트 명시 — 깨짐 방지

python-docx 기본 동작은 시스템 기본 폰트 사용. macOS·Windows·Linux별로 다릅니다 → 한글 깨짐.

```python
# core/docgen/word.py — 폰트 명시
font.name = os.environ.get("AX_KOREAN_FONT", "Apple SD Gothic Neo")
font.eastasia_name = font.name  # ← 이게 핵심
```

`eastasia_name` 안 박아두면 한글 부분만 다른 폰트로 렌더링됩니다 (한자·한글이 섞여 보이는 그 효과).

> "이런 디테일이 자동화 도구의 quality of life입니다. 한 번 잡고 나면 평생 안 깨집니다."

#### md-to-pdf 스킬 — npx tsx 호출

PDF는 weasyprint도 검토했지만 Pango/Cairo 의존성이 macOS에서 OSError 일으키는 케이스 발견 → **md-to-pdf 스킬** (Puppeteer 기반) 채택.

```python
# core/docgen/pdf.py
subprocess.run(
    ["npx", "tsx", "scripts/md-to-pdf.ts", str(md_path), str(pdf_path)],
    check=True,
)
```

> "정확히 어떤 명령어로 호출하는지 적어둡니다. R3-C1 audit 때 'md-to-pdf 정확한 호출 방식이 뭐냐' 질문이 있어서 verbatim으로 적어둔 결과입니다."

#### 청중 예상 질문

- **Q: "한글 폰트 라이선스는?"**
  - A: Apple SD Gothic Neo는 macOS 기본. Windows는 맑은 고딕 (`AX_KOREAN_FONT=맑은 고딕`). 라이선스 우려되시면 나눔고딕 (오픈소스) 추천.
- **Q: "복잡한 표 그리기는?"**
  - A: 단순 표는 python-docx가 잘 그리는데, 복잡한 머지 셀·중첩 표는 코드량이 많아집니다. 그 경우 markdown → md-to-pdf 경로가 더 깔끔.
- **Q: "ChatGPT가 견적서 그리면 안 되나?"**
  - A: ChatGPT는 매번 양식이 미묘하게 달라집니다. 합계 계산도 가끔 틀려요. 회사 견적서는 영구 일관성이 신뢰도 — 코드에 묶여야 합니다.

---

## [0:30 - 0:35] Docgen 블록 2 — case06 정부지원사업 HWPX 자동 작성

> 페르소나: **김사장** · 정부지원사업 신청서 양식 직접 채움 — **30분 → 30초**

### Before (1분)

> "김사장님은 매년 정부지원사업 신청서 4~5건 양식을 직접 채웁니다. 한 건당 8~12 필드, 회사명·대표자·사업자번호·신청금액·매출액. 30분짜리 작업인데 진짜 짜증 나는 건 사업자번호 한 자리 오타가 **제출 후에 발견된다**는 거죠. 거기서 다시 정정 신청 절차…"

### Demo (2~3분)

```bash
uv run python -m cases.case06_hwpx_govt_form_filler.scenario
```

콘솔: `정부지원사업 신청서 HWPX 자동 채움 완료: before 30m → after 0.0s`

- 출력 파일 경로 콘솔에 표시
- **한글 GUI에서 결과 .hwpx 직접 열기** — 회사명/대표자명/사업자등록번호/사업분야/신청금액/매출액/직원수/신청일자 8필드가 양식 우측 칸에 입력된 모습 시각 확인
- `personas/sample_data/grant_data.py`의 `AX_TRADING_GRANT` dict 보여주기 — "이 한 dict가 진실의 출처. 양식 .hwpx만 사업별로 바꾸면 동일 데이터 재사용."

(강사 노트: **자동 미리보기 없음**. rhwp PoC 실패 → Phase 3 연기. 결정 문서: `specs/rhwp-poc-decision.md`. 시연 마지막엔 "한글에서 직접 열기" 단계가 들어갑니다. **한글 미설치 노트북에서는 이 케이스 시연 불가** — 시연 머신 사전 점검 필수.)

(강사 노트: 양식 fixture는 stand-in. 실제 TIPA 양식 아니라 MIT Skeleton.hwpx에 8행 표 주입한 샘플. 도입 시 사업별 양식으로 교체.)

### After + Architecture (1~2분)

- **시간 효과**: 30분 → 30초.
- **검증 게이트**: `verification_passed=True`, `missing_values=[]`. extract_text로 8개 값이 다 들어갔는지 자동 검증. 양식이 셀 위치 잘못 잡으면 missing_values에 즉시 떨어짐.
- **사업자번호 검증**: case08과 동일 모듈러스 알고리즘 재사용 가능 (본 케이스는 채우기에 집중).
- **사용 모듈**:
  - `core/docgen/hwpx.py` — `HwpxEditor` 래퍼 (hwpx-editor 스킬, MIT)
  - `core/docgen/hwp_preview.py::render_preview` — Phase 3 placeholder (`NotImplementedError`)
  - `personas/sample_data/grant_data.py` — 회사 데이터 단일 source

> "회사 데이터가 단일 source에 있어서 양식만 갈아끼우면 매년 다른 사업, 다른 양식에 같은 데이터가 그대로 흘러 들어갑니다. 사업자번호 오타가 **발생할 수 없는 구조**입니다."

#### rhwp PoC 정직성 (R3-H1)

T16에서 rhwp(Rust+WASM HWPX 렌더러) PoC 진행 → **실패**. 이 사실을 강의에서 숨기지 않습니다.

| 옵션 | 결과 | Blocker |
|---|---|---|
| HOP CLI | brew cask로만 존재 (GUI 앱) | CLI 진입점 부재 |
| rhwp WASM + wasmtime | wasmtime 미설치 + 브라우저 의존 | 1일 이상 PoC 필요 |
| rhwp CLI from source | SVG export만 지원 | PDF는 v2.0.0 로드맵 (TBD) |
| LibreOffice headless | 1GB+ 카스크 | HWPX 변환 품질 검증 별도 1일 |
| kordoc (npm) | HWPX → Markdown만 | 표/체크박스 손실 |

> "다 안 됐다는 얘기를 그대로 합니다. PoC는 실패한 사실이 가장 가치 있는 산출물이거든요. Phase 3에서 rhwp v2.0.0이 PDF 출력하거나 LibreOffice 24+ HWPX 필터가 검증되면 그때 자동 미리보기 붙입니다. 결정 문서: `specs/rhwp-poc-decision.md`."

#### 검증 게이트 — extract_text 라운드트립

채우기 → 다시 읽기로 검증:

```python
# 1. fill_form: 양식에 8개 값 채우기
editor.fill_form(template_path, data)

# 2. extract_text: 결과 .hwpx에서 다시 읽기
extracted = editor.extract_text(result_path)

# 3. 8개 값이 다 들어갔는지 확인
missing = [v for v in data.values() if v not in extracted]
verification_passed = len(missing) == 0
```

> "extract_text가 실패하면 verification_passed=False + missing_values=['1234567890']. 양식이 셀 위치 잘못 잡으면 그 자리에서 잡힙니다."

#### 청중 예상 질문

- **Q: "다른 신청서 양식도 됩니까?"**
  - A: `_GRANT_TABLE_ID`와 `_FIELD_ORDER`만 양식별로 한 번 잡으면 됩니다. 사업별 5분 셋업.
- **Q: "한글 미설치 노트북에서는?"**
  - A: 안 됩니다. 시연 환경 전제조건. Phase 3에서 자동 미리보기 붙으면 그때 해결.
- **Q: "사업자번호 검증은?"**
  - A: case08 모듈러스 알고리즘 재사용 가능. 본 케이스는 채우기에 집중하지만 grant_data 입력단에 한 줄 추가만 하면 됩니다.

---

## [전환] OCR 블록 — "이미지를 표로 — 이게 진짜 자동화의 절정"

> "OCR은 사무자동화의 최고 난이도 영역입니다. 이미지에서 데이터 뽑아내는 일이거든요. 그동안은 PaddleOCR 같은 수십 GB 모델 + GPU 필요해서 중소기업 노트북에서 안 돌았는데, 2026년 4월에 Google이 **Gemma 4 E2B/E4B** 멀티모달 LLM 출시하면서 판이 바뀌었습니다. 4GB RAM이면 영수증 OCR이 됩니다. 두 케이스로 보여드립니다."

---

## [0:35 - 0:40] OCR 블록 1 — case07 영수증 100장 OCR (Gemma 4 E2B)

> 페르소나: **박과장** · 영수증 100장 수기 입력 — **3시간 → 1분**

### Before (1분)

> "박과장님이 매월 영수증 100장 수기 입력하는데 3시간. 마감 가까워지면 야근. 영수증 사진 한 장 한 장 보면서 거래일·가맹점·금액 받아치는 일이거든요."

### Demo (2~3분)

5장 빠른 시연:
```bash
uv run python -m cases.case07_ocr_receipt_to_excel.scenario
# input/에 5장만 두면 5초 처리
```

→ 콘솔: `영수증 OCR (5장) 완료: 5.2s` (시연 시 측정)

- Quick Look으로 expense_report.xlsx 열기
- "거래일·가맹점·카테고리·결제수단·금액 5컬럼. 회계SW 임포트 양식 그대로."

100장 전체 시연 시:
```
[OCR] r042.png → 스타벅스 강남점 / 5500원 / 2026-04-15
```
영수증당 약 600ms (시연 환경에 따라 변동), 합산 1분 내외.

(강사 노트: 라이브 시연 시 5장으로 시작. 시간 여유 있으면 100장 전체 시연으로 확장.)

### After + Architecture (1~2분)

- **시간 효과**: 3시간 → 1분.
- **로컬 추론**: **Ollama Gemma 4 E2B** — 영수증 데이터가 외부 클라우드로 안 나감. 외부 API 호출 0건.
- **하드웨어**: E2B는 4GB RAM이면 충분. M1 Air에서도 동작.
- **사용 모듈**:
  - `core/ocr/gemma.py` — Ollama client (timeout + jsonschema validation/retry)
  - `core/ocr/receipt.py` — `ReceiptData` TypedDict, 날짜/금액 정규화
  - `core/excel/writer.py` — 5컬럼 출력

> "영수증 100장이 회사 밖으로 안 나가는 게 핵심입니다. 클라우드 OCR은 영수증 한 장당 데이터가 외부로 송출되거든요. 로컬 Gemma 4는 노트북에서 끝납니다."

(강사 노트: **가상 데이터 한계 명시 — R3-H1 정직성**. 시연한 100장은 Pillow로 합성한 가상 영수증. 실 영수증 환경 100% 동일 X. 도입 전 사용 환경 영수증 10장 hold-out 검증 권장.)

#### Gemma 4 E2B 선택 이유

| 모델 | 메모리 | 영수증당 처리 시간 | 정확도 (영수증 기준) |
|---|---|---|---|
| Gemma 4 E2B | 4GB | ~600ms | 충분 (가맹점·금액·일자) |
| Gemma 4 E4B | 8GB | ~6s | 더 높음 (양식 큰 문서) |
| GPT-4o vision | 클라우드 | ~2s | 매우 높음 (비용+클라우드 송출) |

> "영수증은 가맹점·금액·일자만 정확히 뽑으면 충분합니다. E4B는 영수증한테 오버스펙. 그래서 영수증은 E2B, 세금계산서는 E4B 두 모델 분리."

#### jsonschema validation + retry 패턴

LLM이 JSON을 살짝 잘못 뱉는 경우가 있습니다 (예: 따옴표 누락, 키 이름 다름).

```python
# core/ocr/gemma.py
schema = {
    "type": "object",
    "properties": {
        "merchant": {"type": "string"},
        "amount": {"type": "number"},
        "date": {"type": "string", "format": "date"},
    },
    "required": ["merchant", "amount", "date"],
}

for attempt in range(3):
    response = ollama.chat(...)
    try:
        data = json.loads(response.content)
        jsonschema.validate(data, schema)
        return data
    except (json.JSONDecodeError, jsonschema.ValidationError):
        continue  # 재시도
raise OCRRetryExhausted(...)
```

> "LLM이 JSON 살짝 잘못 뱉는 건 흔합니다. 3회 retry + schema 검증으로 처리. retry 다 실패하면 그 영수증만 따로 워크큐로 빠집니다."

#### 청중 예상 질문

- **Q: "Ollama 모델 다운로드 얼마나 걸려요?"**
  - A: E2B 약 1.5GB. 첫 다운 5~10분. 이후 로컬 캐시.
- **Q: "정확도 99% 보장됩니까?"**
  - A: 단언 못 합니다. 영수증 품질·언어·가맹점 다양성에 따라 변동. 그래서 도입 전 **hold-out 검증 5~10장 필수**. 정확도 측정 코드는 Phase 2.5 후속 (T22 N6).
- **Q: "수기 입력 vs OCR 비교?"**
  - A: 박과장이 영수증당 평균 1분 50초 (수기). OCR은 600ms. 약 180배 차이. 거기에 야근 부담·오타 사라지는 효과.

---

## [0:40 - 0:45] OCR 블록 2 — case08 세금계산서 OCR + 회계 CSV (Gemma 4 E4B)

> 페르소나: **박과장** · 세금계산서 30장 회계SW 수기 입력 — **4시간 → 4분**

### Before (1분)

> "박과장님이 매월 세금계산서 30장 회계SW 입력하는 데 4시간. 더 짜증 나는 건 사업자번호 한 자리 오타 났는데 막상 알게 되는 시점은 **부가세 신고할 때**라는 거죠. 거기서 거꾸로 추적하면 또 반나절."

### Demo (2~3분)

5장 빠른 시연:
```bash
uv run python -m cases.case08_ocr_invoice_to_csv.scenario
# input/에 5장만 두면 30초 처리
```

→ 콘솔: `세금계산서 OCR (5장) 완료: 30.4s` (시연 시 측정)

- Quick Look으로 `invoices_utf8.csv` 열기 — Excel이 BOM 자동 인식 → 한글 깨짐 0
- "거래일·거래번호·공급자번호·공급자명·공급받는자번호·공급받는자명·공급가액·부가세·합계 9컬럼. 세금계산서 표준 그대로."

30장 전체 시연 (3분):
```
[OCR] inv_007.png → INV-2026-00007 / 공급자 (주)... / 공급가액 350,000원 (면세)
```
- 면세 거래는 `vat=0`으로 자동 인식
- `validate_biznum` + vat 일치성 검증 통과 28건만 verified
- 의도적으로 깨놓은 2건은 `validation_failures.json`으로 분리

**Dual encoding** 시연 (시간 여유 시):
- `invoices_utf8.csv` Excel로 열기 — 한글 정상 + BOM 자동 인식
- `invoices_cp949.csv` 레거시 회계SW (예: 더존) import 경로로 열기

### After + Architecture (1~2분)

- **시간 효과**: 4시간 → 4분.
- **사업자번호 모듈러스 검증**: 국세청 알고리즘. OCR이 한 자리 잘못 읽으면 체크섬에서 즉시 fail → 워크큐로 분리.
- **dual encoding**: utf-8 BOM (최신 Excel) + cp949 (레거시 ERP) 두 CSV 동시 export. "저희 환경은 다릅니다" 한마디에 미팅 안 끊김.
- **모델 선택 = 트레이드오프**: E2B (영수증, ~600ms) vs E4B (세금계산서 양식 큰 거, ~6s).
- **사용 모듈**:
  - `core/ocr/gemma.py` — Ollama client (E4B model)
  - `core/ocr/invoice.py` — 사업자번호 모듈러스 + 면세 분기 (Phase 2 Group F T14)
  - 회계 CSV export — `csv` 표준 라이브러리

> "사업자번호 체크섬 검증이 자동이라 '오타로 잘못 친 비번호'가 발생할 수 없는 구조입니다. 부가세 신고에서 발견되는 일 자체가 사라집니다."

(강사 노트: **가상 데이터 한계 명시**. 30장 합성 + 사업자번호도 알고리즘 충족 임의값. 의도적으로 2장 체크섬 깨놨음. 도입 전 사용 환경 5장 hold-out 검증 권장.)

#### 사업자번호 모듈러스 알고리즘

국세청 공식 검증 알고리즘:

```python
def validate_biznum(biznum: str) -> bool:
    digits = [int(d) for d in biznum if d.isdigit()]
    if len(digits) != 10:
        return False
    weights = [1, 3, 7, 1, 3, 7, 1, 3, 5]
    checksum = sum(d * w for d, w in zip(digits[:9], weights))
    checksum += (digits[8] * 5) // 10  # 9번째 자리 보정
    check_digit = (10 - checksum % 10) % 10
    return check_digit == digits[9]
```

> "이 한 함수로 OCR이 한 자리 잘못 읽었는지 즉시 잡힙니다. 부가세 신고 후에 알게 되는 일 자체가 사라집니다."

#### dual encoding — utf-8 BOM vs cp949

한국 회계SW 인코딩 분포:

- 최신 회계SW (이카운트, 더존스마트A 등): **utf-8** (BOM 자동 인식)
- 레거시 ERP·회계SW: **cp949 only** (utf-8 넣으면 한글 깨짐)
- Excel: 두 인코딩 다 지원하나 BOM 없으면 cp949로 오인

이 프로젝트는 두 CSV 동시 export:

```python
# core/ocr/invoice.py — Phase 2 T14
csv_export(rows, "invoices_utf8.csv", encoding="utf-8-sig")  # BOM 포함
csv_export(rows, "invoices_cp949.csv", encoding="cp949", errors="replace")
```

> "회계SW가 어떤 인코딩 받든 그 자리에서 import 가능. 둘 중 하나만 export하면 시연 현장에서 '저희 환경은 다릅니다' 들으면 미팅이 끊겨요. 그래서 둘 다 만듭니다."

#### 청중 예상 질문

- **Q: "면세 거래는?"**
  - A: vat=0 케이스를 검증 게이트가 통과시키도록 명시 분기. 면세사업자 거래도 정상 처리. validation_failures.json에 안 들어갑니다.
- **Q: "세금계산서 사이즈 큰데 6초면 충분?"**
  - A: 충분합니다. E4B가 양식 큰 거 정확도 확보용. 6초 × 30장 = 3분.
- **Q: "도장·서명 영역 어떻게 처리?"**
  - A: 현재는 도장이 인식 결과에 영향을 미칠 수 있습니다. Phase 3에서 도장·서명 영역 제거 후 OCR 정확도 향상 검토.
- **Q: "홈택스 자동 신고는?"**
  - A: **스코프 외**. CSV export까지가 본 시스템. 홈택스 자동 제출은 약관 리스크 + Phase 3 검토. 외부 자동 제출은 미스코프.

---

## [전환] AI 블록 — "사람의 판단·정리 영역 보조"

> "마지막 카테고리 AI입니다. AI는 만능이 아니에요. 답신 메일 톤 잡기 + 회의록 정리 두 영역만 보여드립니다. 둘 다 사람이 검토 후 발신하는 구조 — AI가 직접 보내는 게 아니라 **AI가 초안, 사람이 최종**입니다."

---

## [0:45 - 0:50] AI 블록 1 — case09 거래처 응대 메일 AI 초안 3안

> 페르소나: **이대리** · 답신 한 통에 톤 고민 — **10분 → 8초**

### Before (1분)

> "이대리님이 거래처 답신 한 통에 톤 고민 10분. 친근하게 갈지, 정중하게 갈지, 단호하게 갈지. 하루 50통이면 8시간이에요. 다른 일은 언제 합니까."

### Demo (2~3분)

```bash
DEMO_SAFE=1 uv run python -m cases.case09_ai_email_drafter.scenario
```

(안전 모드 권장 — 캐시 응답으로 시연 안정성 확보)

→ `drafts.json` 열기 → 3가지 톤 비교:
- **옵션 1**: 신중·보수
- **옵션 2**: 친근·관계 강화
- **옵션 3**: 명확·간결

(강사 노트: "ChatGPT랑 뭐가 달라요?" 질문이 나올 시 — **사내 톤 + 거래 이력이 prompt에 자동 주입**됨을 강조. 영업팀 신입도 부장 톤으로 답신.)

5분 모드 추가 시연:
- **모델 폴백**: Gemini 2.5 Flash → Claude Haiku 4.5 → GPT-4o-mini → safe-fallback
- 비용·지연 비교 (시연 시 측정)

### After + Architecture (1~2분)

- **시간 효과**: 10분 → 8초.
- **차별화**: 단순 글쓰기가 아니라 **이 회사 거래 이력 기반 답신**. ChatGPT 웹UI 대비.
- **사용 모듈**:
  - `core/ai/client.py::chat` — OpenRouter (openai SDK 호환) + 4단계 폴백 체인
  - `core/ai/prompts.py` — 사내 톤 + 거래 이력 주입 템플릿
  - `core/ai/tasks.py::draft_email` — 3안 생성
  - `core/common/safe_mode.py` — DEMO_SAFE 토글, deterministic 캐시 응답

> "영업팀 신입도 부장 톤으로 답신 씁니다. 그리고 모델 하나 죽어도 자동 폴백되니까 시연 끊길 일 없습니다."

#### 모델 폴백 체인 — 시연 안정성의 비밀

```python
# core/ai/client.py
MODEL_PRIORITY = [
    "google/gemini-2.5-flash",      # 1차: 빠르고 저렴
    "anthropic/claude-haiku-4.5",   # 2차: Gemini 다운 시
    "openai/gpt-4o-mini",           # 3차: 둘 다 다운 시
    # 4차: force_safe() — 캐시된 deterministic 응답
]
```

> "현장 시연에서 모델 한 개 503 나는 거 자주 봅니다. 그래서 4단계 폴백. Wi-Fi가 끊겨도 force_safe()로 캐시 응답 — 시연 절대 안 끊깁니다."

#### 사내 톤 + 거래 이력 prompt 주입

ChatGPT 웹UI는 매번 컨텍스트를 직접 입력해야 합니다. 이 시스템은 코드에 묶여 있어요:

```python
# core/ai/prompts.py
SYSTEM = """
당신은 AX상사 영업 답신 작성 보조입니다.
회사 톤: 정중하나 단호. 줄임말 X. 거래처에 신뢰감.
"""

USER = """
[과거 거래 이력]
{history}

[수신 메일]
{incoming}

[요청] 3가지 톤 (보수/친근/간결)으로 답신 초안 작성.
JSON 형식으로 반환.
"""
```

> "사내 톤은 한 번 정의하면 평생. 거래처별 과거 거래 이력은 데이터에서 자동 주입. ChatGPT가 매번 컨텍스트 입력하는 시간이 없습니다."

#### deterministic 캐시 — DEMO_SAFE 토글

`DEMO_SAFE=1` 환경변수 설정 시:

```python
# core/common/safe_mode.py
def chat(prompt, **kwargs):
    if is_safe():  # DEMO_SAFE=1 + no API key
        cache_key = sha1(prompt)
        return get_cached_response(cache_key) or generate_safe_fallback()
    # 정상 흐름
    ...
```

> "시연 시 같은 입력은 같은 응답이 나옵니다 (deterministic). 라이브 시연 재현 가능하니까 강의 리허설할 때도 매번 결과 다를 일 없습니다."

#### 청중 예상 질문

- **Q: "AI가 거래처 메일 답신 잘못 쓰면?"**
  - A: 발송 전 이대리 검토 단계 필수. AI는 초안 3안 생성, 발송은 사람.
- **Q: "비용은?"**
  - A: Gemini 2.5 Flash 기준 1만 토큰당 약 $0.001. 답신 1통 약 0.5만 토큰 → $0.0005. 하루 50통이면 $0.025 (약 35원). 거의 무료.
- **Q: "시크릿 키 관리는?"**
  - A: `secrets_mask.py`가 로그·콘솔 자동 마스킹. `.env` 파일은 git ignore + 1Password 보관. 레포에 노출 0.

---

## [0:50 - 0:55] AI 블록 2 — case10 회의록 텍스트 → 요약·액션·담당자

> 페르소나: **김사장** · 회의 후 정리 — **30분 → 5초 (1건) / 1분 (5건)**

### Before (1분)

> "김사장님 매 회의 후 정리·할당·기한 메모를 손으로 30분간 정리. 다음 미팅 들어가는데 빠듯해요. 누가 뭐 하기로 했는지 또 까먹고."

### Demo (2~3분)

```bash
uv run python -m cases.case10_ai_meeting_summarizer.scenario
```

- 출력 폴더에 5개 markdown 파일 생성. 콘솔: `회의록 요약 (5건) 완료` (시연 시 측정)
- `meeting_summary_m001_monthly_sales.md` 열기
- **김사장 페르소나 인용**: "회의 1건이 5초. 박과장은 5월 5일까지 미수금 회수, 이대리는 5월 12일까지 콩코드물산 견적. 메모 안 잃어버리고 카톡으로 바로 공유 가능."

**owner hallucinate 방지** 시연:
- `_meeting_meta.json` 열기 → attendees ground truth
- "AI가 명단 외 사람한테 일을 떠넘기는 hallucinate 문제, attendees ground truth로 강제. m002에는 김사장·박과장·최주임만 등록 → LLM이 다른 이름 만들어내면 즉시 fail."

### After + Architecture (1~2분)

- **시간 효과**: 30분 → 1건 5초, 5건 1분.
- **음성 입력은 Phase 3** (whisper deferred). 결정 문서: `specs/case10-whisper-decision.md`. 현재는 **텍스트 회의록 입력만**. 회의는 녹음만 해두고 서기 노트 또는 자동 STT 결과를 입력으로 넣는 구조.
- **사용 모듈**:
  - `core/ai/tasks.py::summarize_meeting` — `MeetingSummary` / `ActionItem` TypedDict
  - `core/ai/client.py` — OpenRouter 폴백
  - attendees ground truth 검증

> "AI가 명단 외 사람한테 액션 떠넘기지 않도록 ground truth 강제했습니다. 도입 환경에서 가장 많이 받는 클레임이 그거였거든요 — '내가 안 한 일이 내 액션으로 들어왔다'."

#### owner hallucinate 방지 — attendees ground truth 강제

```python
# core/ai/tasks.py::summarize_meeting
def validate_action_items(items: list[ActionItem], attendees: list[str]) -> None:
    for item in items:
        if item["owner"] not in attendees:
            raise OwnerHallucinated(
                f"Action owner '{item['owner']}' not in attendees {attendees}"
            )
```

`_meeting_meta.json`:
```json
{
  "meeting_id": "m002_overdue_review",
  "attendees": ["김사장", "박과장", "최주임"]
}
```

LLM이 "이대리에게 X를 할당"이라고 환각하면 그 자리에서 raise. retry 또는 워크큐 분리.

> "이게 진짜 운영 환경에서 LLM 도입 막는 1순위 이슈입니다. 명단 외 사람한테 일 떠넘기는 거. ground truth로 강제 안 하면 도입 첫 주에 신뢰 잃습니다."

#### due_date 형식 검증

```python
# T12.5 fixer commit에서 추가
def validate_due_date(due: str) -> str:
    # ISO 8601 (YYYY-MM-DD)만 허용
    datetime.strptime(due, "%Y-%m-%d")
    return due
```

> "AI가 '다음 주 월요일' 같은 자연어로 due_date 뱉으면 다음 단계 시스템에서 못 씁니다. ISO 8601 강제."

#### 청중 예상 질문

- **Q: "음성 회의록 STT는 정말 Phase 3?"**
  - A: 네. whisper 로컬 모델 1GB + ffmpeg 의존성이 무거워서 Phase 2에서 보류. 시연 임팩트는 텍스트만으로도 충분 — "30분 → 5초"는 동일.
- **Q: "회의록을 카톡에 바로 공유하면?"**
  - A: 카톡 자동발송은 약관 리스크. Discord 사내 채널 또는 Gmail 공유 추천. case04 Discord 패턴 재사용 가능.
- **Q: "회의록 5건 동시 처리?"**
  - A: 현재는 순차. 병렬은 OpenRouter rate limit 고려해 Phase 3 검토. 5건 1분이면 충분히 빠름.
- **Q: "행동 항목이 누락되면?"**
  - A: 회의록 본문에 명시 안 된 액션은 AI도 못 뽑습니다. 그래서 "회의 끝에 액션 정리 단계" 자체를 넣는 게 좋습니다 — 이건 프로세스 권고.

---

## [전환] Q&A 블록 — 5분 마지막 정리

> "여기까지 10개 케이스 보셨습니다. 마지막 5분은 자주 받는 질문 + 다음 단계 1:1 워크숍 안내드립니다."

---

## [0:55 - 1:00] Q&A — 자주 받는 질문 + 다음 단계

### Q1. "보안은 안전한가요? 회사 데이터가 외부로 나가지 않나요?"

세 단계로 답합니다:

1. **Local-first** — case07/08 OCR은 **Ollama 로컬 추론**. 영수증·세금계산서 한 장도 외부 송출 0건.
2. **Secrets 자동 마스킹** — `core/common/secrets_mask.py`가 OpenRouter 키, Gmail OAuth, SMTP 비밀번호, Discord webhook URL을 로그·콘솔에서 자동 마스킹.
3. **Safe mode 격리** — `DEMO_SAFE=1` 토글로 외부 API 호출 전부 차단 + deterministic 캐시 응답. 시연·교육·QA 환경에서 동일 코드 그대로 안전 반복.

> "그리고 시크릿은 1Password 또는 age 외부 보관. 레포에는 `.no_real_data` sentinel만 들어갑니다."

### Q2. "한글 양식 (HWPX) 미리보기는 자동화 안 되나요?"

오늘 case06에서 보셨듯 **한글 GUI에서 직접 열어 확인**하는 흐름입니다. rhwp(Rust+WASM HWPX 렌더러) PoC 진행했지만 v0.7.9 시점 PDF/PNG export 미지원 → **Phase 3로 연기**. 결정 문서: `specs/rhwp-poc-decision.md`.

> "rhwp v2.0.0이 PDF export 추가하거나 LibreOffice HWPX 필터가 검증되면 그때 자동 미리보기 붙입니다. 현재는 한글 설치된 노트북에서만 case06 시연이 가능하다는 점은 운영 매뉴얼에 명시했습니다."

### Q3. "음성 회의록은 언제 됩니까?"

case10 demo에서 보셨듯 **현재는 텍스트 회의록 입력**입니다. 음성 → 텍스트 STT는 **Phase 3**. 결정 문서: `specs/case10-whisper-decision.md`. whisper 로컬, OpenRouter audio API, macOS Speech 세 옵션 비교 후 결정 예정.

> "지금은 회의 녹음 + 자동/수동 STT 결과를 텍스트로 넣으시면 됩니다. STT가 붙어도 그 뒤 요약·액션·담당자 파이프라인은 오늘 보신 그대로입니다."

### Q4. "도입 시간·비용은?"

케이스별로 다릅니다.

| 케이스 군 | 도입 기간 (사용 환경 적용) | 비고 |
|---|---|---|
| Excel (case01, 02) | **1주** | column_map 매핑 + 회사 양식 적용 |
| Messaging (case03, 04) | **1~2주** | Gmail OAuth/SMTP 셋업 + Discord 채널 정책 |
| Docgen (case05, 06) | **1~2주** | 회사 로고·CI 적용 + (case06) 사업별 양식 셀 매핑 |
| OCR (case07, 08) | **2주** | Ollama 셋업 + 사용 환경 hold-out 검증 (5~10장) |
| AI (case09, 10) | **1~2주** | 사내 톤 정의 + 거래 이력 컬럼 매핑 |

> "10개 다 도입하시려면 4~6주. 한두 케이스만 우선 도입하면 1~2주."

### Q5. "코드는 어디서 받나요?"

AX 컨설팅 계약 후 **`core/` 라이브러리 import 권한** 제공. 다음 컨설팅 프로젝트에 가셔도 같은 모듈 import해 자체 데이터로 재사용 가능합니다.

> "한 번 만들면 평생 자산. 인트로에서 약속드린 그대로입니다."

### 다음 단계 — 1:1 워크숍 안내 (30초)

오늘 60분이 시작점입니다. 본격 적용 전 **자기 업무 매핑 워크숍**을 진행합니다.

1. 청중 회사 업무를 5개 카테고리에 매핑
2. 우선 도입 케이스 1~2개 선정 (시간 효과 큰 순)
3. 사용 환경 데이터 5~10건으로 hold-out 검증
4. 1주 PoC → 도입 결정

> "오늘 케이스 중에 '이건 우리도 똑같다' 잡힌 거 있으시면 워크숍 신청 부탁드립니다. 끝까지 봐주셔서 감사합니다."

### Q6. (자주 받는 추가 질문) "사용 환경 hold-out 검증이 뭡니까?"

도입 직전에 청중 회사의 **실제 데이터 5~10건**을 따로 빼두고 (training에 안 쓰고), 그것만으로 시스템 정확도를 측정하는 절차입니다.

- case07: 영수증 10장 hold-out → 가맹점 일치율 / 금액 일치율 / 일자 일치율 측정
- case08: 세금계산서 5장 hold-out → 사업자번호·공급가액·부가세 정확도
- case01/02: 매출·거래명세서 1개월 데이터 hold-out → 합계 일치 검증

> "이게 빠지면 '시연은 잘되는데 실제 환경에선 안 된다' 사고가 납니다. 컨설팅 1주차에 무조건 들어가는 단계."

### Q7. (자주 받는 추가 질문) "오타·실수가 정말 사라지나요?"

**완벽히 사라지진 않습니다.** 다만 위치가 바뀝니다.

| 단계 | 수기 작업 오타 | 자동화 오타 |
|---|---|---|
| 입력 단계 | 100건당 평균 1~2건 | 0건 (입력은 사람이 안 함) |
| 검증 단계 | 사후 검수 안 하면 누락 | 자동 검증 게이트 (모듈러스·체크섬) |
| 운영 단계 | 부가세 신고에서 발견 | 입력 즉시 발견 |

> "오타가 발생하더라도 **즉시 발견**되는 구조로 바뀝니다. 부가세 신고 후 발견되는 일 자체가 사라집니다."

### Q8. (자주 받는 추가 질문) "이걸 직원이 운영할 수 있나요?"

세 가지 운영 모드가 있습니다.

1. **운영자 모드 (관리자 1명)**: `runner.py` 실행 → 메뉴에서 케이스 선택. CLI 익숙한 직원이 담당.
2. **자동 모드 (cron/launchd)**: 매월 1일 새벽 case01 자동 실행, 매주 월요일 09:00 case04 자동 실행. 운영자 개입 0.
3. **웹UI 모드 (Phase 3)**: Streamlit/FastAPI로 버튼 UI. CLI 불편한 직원도 사용 가능. Phase 3 검토 중.

> "오늘 시연은 1번. 도입 후 안정화되면 2번 → Phase 3에서 3번. 단계적 도입 추천."

### Q9. (자주 받는 추가 질문) "이 코드는 누가 유지보수합니까?"

세 가지 옵션:

1. **AX 컨설팅 유지보수 계약** (월 정액): 신규 케이스 추가, 양식 변경 대응, 모델 폴백 업데이트
2. **사내 IT 인력에 인수인계**: 1주 트레이닝 + 코드 워크스루. Python 기본만 알면 충분 (대부분 모듈은 column_map 매핑만 변경)
3. **하이브리드**: 1차 사내, 2차 컨설팅. 신규 케이스만 외주.

> "1번이 처음에 가장 안전하고, 안정화되면 2번으로 전환하는 회사가 많습니다."

### Q10. (자주 받는 추가 질문) "Phase 3에는 뭐가 들어가나요?"

오늘 시연하지 않은 영역:

- **case10 음성 입력 (whisper STT)** — 결정 문서: `specs/case10-whisper-decision.md`
- **case06 자동 미리보기** — rhwp v2.0.0 또는 LibreOffice HWPX 필터 검증 후 결정
- **회귀 테스트 자동화** — 매월 1회 사용 환경 데이터로 정확도 자동 측정
- **웹UI** — Streamlit 또는 FastAPI 기반 GUI
- **`core/` 사내 패키지 (`flowcoder-office-tools`)** — pip install로 다른 프로젝트에서 import

> "Phase 3는 청중 회사 실제 도입 후 운영 데이터 기반으로 우선순위 결정합니다. 지금 정해놓고 가는 게 아닙니다."

### 다음 단계 — 1:1 워크숍 안내 (30초)

오늘 60분이 시작점입니다. 본격 적용 전 **자기 업무 매핑 워크숍**을 진행합니다.

1. **W1 (1주차)**: 청중 회사 업무를 5개 카테고리에 매핑 + 우선 도입 케이스 1~2개 선정
2. **W2 (2주차)**: 사용 환경 데이터 5~10건으로 hold-out 검증 + 정확도 측정
3. **W3 (3주차)**: 1주 PoC + 운영자 트레이닝
4. **W4 (4주차)**: 도입 결정 + 유지보수 계약 셋업

> "1~4주가 표준 도입 사이클입니다. 케이스 수에 따라 4~8주로 늘어날 수 있습니다."

### 마무리 인사 (30초)

> "오늘 보여드린 10개 케이스가 답이 아닙니다. 청중 여러분 회사의 사무 업무 중 **반복 + 시간 많이 쓰는 부분 + 오타 위험 있는 부분** 세 조건이 겹치는 영역이 자동화 후보입니다. 오늘 케이스 매핑을 보시고 '아 이건 우리도 똑같네' 한 영역이 떠오르셨다면 그 영역부터 시작하시면 됩니다. 워크숍에서 뵙겠습니다. 감사합니다."

(강사 노트: 박수 받고 무대 내려가기 전에 명함·QR코드 스크린에 띄움. 워크숍 신청 링크 또는 이메일.)

---

## 준비물 체크리스트 (시연 직전 운영자용)

### 필수 (모든 케이스)

- [ ] **`uv run python runner.py --check --strict` 통과** — Ollama warmup + Discord webhook ping + OpenRouter 키 검증 + npx 경로 확인
- [ ] **OPENROUTER_API_KEY** 설정 (case09, case10 라이브)
- [ ] **DISCORD_WEBHOOK_URL** 설정 (case02, case04 라이브)
- [ ] 출력 폴더 비우기 — `output/` 이전 시연 잔여물 제거 (`.gitkeep` 보존)
- [ ] 노트북 모니터 + 외부 모니터 두 개 (Discord 채널 미리 띄워 둠)
- [ ] Wi-Fi 안정성 점검 + 모바일 핫스팟 백업

### 케이스별

- [ ] **case01**: `personas/sample_data/vendors/` 12개월 파일 존재
- [ ] **case02**: Discord webhook 채널 권한 + 임베드 색상 표시 가능
- [ ] **case03**: `personas/sample_data/quote_dispatch_list.xlsx` 50건, `npx tsx` PATH 확인. (라이브) Gmail OAuth 또는 SMTP 환경변수
- [ ] **case04**: `personas/sample_data/overdue_invoices.xlsx` 60건 (24/18/12/6 분포)
- [ ] **case05**: `personas/sample_data/quote_requests.xlsx` 10 requests / 42 rows. Apple SD Gothic Neo (또는 `AX_KOREAN_FONT` 폰트) 시스템 설치
- [ ] **case06**: **한글 GUI 설치 확인** (한글 미설치 노트북에서는 시연 불가). `personas/sample_data/forms/grant_application_template.hwpx` 존재. `personas/sample_data/grant_data.py` `AX_TRADING_GRANT` dict
- [ ] **case07**: Ollama 데몬 + `gemma4:e2b` 모델 pull 완료. `personas/sample_data/receipts/` 100장
- [ ] **case08**: Ollama 데몬 + `gemma4:e4b` 모델 pull 완료. `personas/sample_data/invoices_scanned/` 30장. (utf-8 BOM + cp949) 두 CSV 출력 경로 확인
- [ ] **case09**: 안전 모드 권장 (`DEMO_SAFE=1`) — 캐시 응답으로 시연 안정성. 라이브 모드 시 OpenRouter 키 + 폴백 모델 4개 검증
- [ ] **case10**: `personas/sample_data/meetings/` 5건 텍스트 회의록 + `_meeting_meta.json` attendees ground truth

### 시연 실패 fallback

- [ ] **외부 API 다운**: `DEMO_SAFE=1` 토글 → 모든 외부 호출 차단 + deterministic 캐시 응답으로 동일 흐름 시연
- [ ] **Discord 알림 안 옴**: webhook URL 재확인 + 마스킹된 로그에서 4xx/5xx 확인
- [ ] **case06 한글 미설치**: 케이스 스킵 + Q&A에서 "rhwp PoC 결과" 1분 설명으로 대체
- [ ] **case07/08 Ollama 다운**: 5장 시연 생략 + 사전 녹화 결과 xlsx/csv Quick Look으로 대체
- [ ] **데모 도중 시간 초과**: case 단축 우선순위 — case08 (4분) → case07 (1분) → case10 (5건) → case03 (50건). 즉, 긴 케이스 먼저 줄이기

---

## 부록 A — 참고 문서

- 케이스별 시연 대본 (1/3/5분): `docs/demo_scripts/case01.md` ~ `case10.md`
- 시연 리허설 로그: `docs/demo_scripts/rehearsal_log.md`
- rhwp PoC 결정: `specs/rhwp-poc-decision.md`
- whisper deferral 결정: `specs/case10-whisper-decision.md`
- Phase 2 plan v2: `specs/2026-05-01-phase2-plan.md`
- 페르소나: `personas/company.md`, `personas/characters.md`
- 익명화 정책: `personas/anonymization_policy.md`

---

## 부록 B — 핵심 모듈 레퍼런스

청중이 이후 자기 프로젝트에 import해 쓸 수 있는 모듈 빠른 참조.

### B.1 Excel 모듈 (`core/excel/`)

| 모듈 | 주요 함수 | 용도 |
|---|---|---|
| `reader.py` | `read_vendors(folder, column_map)` | 다중 엑셀 파일 일괄 읽기 |
| `merger.py` | `merge_by_vendor_month(rows)` | 거래처×월 기준 병합 |
| `pivot.py` | `pivot_table(rows, index, columns, values)` | 피벗 + 합계 행 |
| `writer.py` | `write_report(path, rows, chart=True)` | xlsx + 차트 |
| `validator.py` | `detect_unit_price_outliers(rows, threshold)` | LOO z-score 이상치 |

### B.2 Messaging 모듈 (`core/messaging/`)

| 모듈 | 주요 함수 | 용도 |
|---|---|---|
| `discord.py` | `send(content, webhook_url)` | Discord webhook 단일 patch point |
| `discord.py` | `send_with_level(content, level)` | 단계별 임베드 색상 (friendly/neutral/strict/final) |
| `email.py` | `build_message(to, subject, body, attachments)` | multipart MIME 생성 + XSS escape |
| `email.py` | `send(message)` | Gmail API + SMTP 폴백 |

### B.3 Docgen 모듈 (`core/docgen/`)

| 모듈 | 주요 함수 | 용도 |
|---|---|---|
| `template.py` | `render_html_string(template_str, **ctx)` | Jinja2 + autoescape |
| `word.py` | `build_quote(data, output_path)` | python-docx 견적서 (한글 폰트 명시) |
| `pdf.py` | `md_to_pdf(md_path, pdf_path)` | npx tsx scripts/md-to-pdf.ts 호출 |
| `hwpx.py` | `HwpxEditor(template_path)` | hwpx-editor 스킬 래퍼 (sys.path.insert) |
| `hwp_preview.py` | `render_preview(hwpx, format="pdf")` | Phase 3 placeholder (NotImplementedError) |

### B.4 OCR 모듈 (`core/ocr/`)

| 모듈 | 주요 함수 | 용도 |
|---|---|---|
| `gemma.py` | `extract(image_path, prompt, schema)` | Ollama Gemma 4 client + jsonschema retry |
| `receipt.py` | `parse_receipt(image_path) -> ReceiptData` | E2B 모델 + 날짜/금액 정규화 |
| `invoice.py` | `parse_invoice(image_path) -> InvoiceData` | E4B 모델 + 사업자번호 모듈러스 |
| `invoice.py` | `validate_biznum(biznum: str) -> bool` | 국세청 모듈러스 알고리즘 |

### B.5 AI 모듈 (`core/ai/`)

| 모듈 | 주요 함수 | 용도 |
|---|---|---|
| `client.py` | `chat(messages, **kwargs)` | OpenRouter + 4단계 폴백 + safe_mode short-circuit |
| `prompts.py` | `EMAIL_DRAFT_PROMPT`, `MEETING_SUMMARY_PROMPT` | 사내 톤·거래 이력 주입 템플릿 |
| `tasks.py` | `draft_email(incoming, history, tones)` | 3안 메일 초안 |
| `tasks.py` | `summarize_meeting(text, attendees)` | 요약·액션·담당자 자동 추출 |

### B.6 Common 모듈 (`core/common/`)

| 모듈 | 주요 함수 | 용도 |
|---|---|---|
| `config.py` | `load()` | .env + 환경변수 통합 로드 (load_dotenv 단일경로) |
| `safe_mode.py` | `intercept()`, `is_safe()`, `force_safe()` | unittest.mock 기반 외부 호출 차단 + 캐시 |
| `secrets_mask.py` | `mask(text)` | OpenRouter/Gmail/SMTP/Discord 자동 마스킹 |
| `timer.py` | `Timer("작업명", before_minutes=X)` | before/after 시간 비교 출력 |
| `demo_logger.py` | `demo_logger` | rich console + 시연용 출력 형식 |

---

## 부록 C — 강의 변형 — 시간/대상별

오늘 표준은 60분이지만 청중·시간에 따라 변형 가능.

### C.1 30분 압축 강의

- 인트로 3분 (페르소나 + 카테고리만)
- 5개 카테고리 × 1 케이스 = 5분 × 5 = 25분
  - case01 (Excel 대표)
  - case04 (Messaging 대표 — Discord)
  - case05 (Docgen 대표 — Word/PDF)
  - case07 (OCR 대표 — E2B)
  - case09 (AI 대표 — 메일 초안)
- Q&A 2분

> 30분은 임팩트만. case06 HWPX·case08 세금계산서 같은 깊이 있는 케이스는 빠짐.

### C.2 90분 확장 강의

60분 + 30분 추가:

- 워크숍 시뮬레이션 20분 (청중 회사 업무 매핑 실습)
- 도입 단계 상세 10분 (W1~W4 일정 + 비용)

### C.3 고객 미팅 5~10분 (압축)

- 5분 미팅: case01 + case04 + case09 (엑셀+디스코드+AI 한 번에)
- 10분 미팅: case01 + case03 + case07 + case09 + case10

### C.4 강의 60분 (오늘 표준)

10개 케이스 × 5분 = 50분 + 인트로 5분 + Q&A 5분.

---

## 부록 D — 시연 환경 트러블슈팅 플레이북

라이브 시연에서 자주 발생하는 문제 + 즉시 대응법.

### D.1 Wi-Fi가 끊겼다

**증상**: case03/09/10 시연 중 OpenRouter API 호출 실패.

**대응**:
1. `DEMO_SAFE=1` 환경변수 토글 → 외부 호출 차단 + deterministic 캐시 응답
2. 시연 흐름 그대로 진행 (출력만 "[SAFE-FALLBACK ...]" 마커)
3. 청중에게 "안전 모드로 전환했습니다" 한 마디

> safe_mode 자체가 시연 fallback 설계. 시연 끊길 일 0.

### D.2 Discord webhook이 안 받아들인다

**증상**: case02/04 시연 중 콘솔에 `discord 405` 또는 `429` 에러.

**대응**:
1. `runner.py --check --strict` 재실행 → webhook 핑 확인
2. 마스킹된 webhook URL 확인 (`secrets_mask.py`가 마스킹) → 환경변수 정확히 입력됐는지 점검
3. 429 (rate limit)면 30초 대기 후 재시도
4. 최후 수단: webhook 화면 캡처를 미리 띄워둔 게 있으면 청중에게 보여주고 "이런 식으로 옵니다" 한 마디로 넘어감

### D.3 Ollama 모델이 응답이 없다

**증상**: case07/08 시연 중 `ollama.chat` 30초+ hang.

**대응**:
1. `ollama list` 확인 → `gemma4:e2b` 또는 `gemma4:e4b` 모델 존재 여부
2. 미설치면 `ollama pull gemma4:e2b` 즉석 실행 (1.5GB, 5~10분 소요 — 시연 중 어렵)
3. 시연 중 미설치 발견 시: case07/08 스킵 + Phase 1 케이스로 5분 채우기 + Q&A에서 OCR 영역 별도 설명

### D.4 한글 GUI가 없다 (case06)

**증상**: 시연 노트북에 한글 미설치.

**대응**:
- **사전 점검 단계**: 시연 30분 전에 `personas/sample_data/forms/grant_application_template.hwpx` 한 번 열어보기
- **시연 중 발견**: case06 실행만 하고 결과 .hwpx는 미리 캡처해둔 스크린샷으로 대체. "정확히는 양식이 이렇게 채워집니다" 한 마디.

### D.5 시간이 부족하다 (40분쯤 됐는데 case06 끝)

**증상**: 페이스 늦어져서 OCR 두 개 + AI 두 개 = 20분 남았는데 시간은 15분.

**우선순위 단축**:
1. case08 (4분 시연) → 1분으로 압축. 5장만 시연 + 결과 화면만 보여주기
2. case07 (1분 시연) 그대로 유지
3. case10 (1분 시연 — 5건) → 30초로 압축. 파일 1건만 펼쳐 보여주기
4. case03 (50건) → 5건만 시연

> "긴 케이스 먼저 줄이는 원칙. 짧은 케이스를 더 줄이지 말고 긴 케이스부터."

### D.6 청중이 너무 조용하다

**증상**: 인트로 끝났는데 반응 0.

**대응**:
- case01 Before에서 페르소나 거명 강하게: "박과장님 같은 분 회사에 한 명씩 다 계시잖아요?"
- 첫 데모 결과 나오면 강사가 먼저 "와 빠르네요" 한 마디 → 청중 분위기 풀림
- Q&A 시간에 강사가 직접 가상 질문 던지기: "자주 받는 질문이 '보안은 안전한가요?' 인데요…"

### D.7 청중이 너무 시끄럽다 (질문 폭주)

**증상**: case02 끝나고 질문 5개 동시에 들어옴.

**대응**:
- "Q&A는 마지막 5분에 다 답변드릴게요. 지금은 일단 끝까지 보시고 나서…"
- 메모지에 질문 키워드 받아두고 마지막 Q&A에서 일괄 답변
- 시간 부족하면 "워크숍에서 다루겠습니다" 클로징

---

## 부록 E — 아키텍처 deep-dive (강사용 백업 자료)

청중이 "이게 뭐가 특별합니까" 깊게 물을 때 답변용.

### E.1 단일 patch point 원칙

**문제**: 시연·교육·QA 환경에서 외부 API 호출이 진짜로 나가면 사고.

**나쁜 패턴**:
```python
# 시나리오마다 자체 wrap
def case04_run():
    if os.getenv("DEMO_SAFE"):
        return mock_send(...)  # 이런 코드가 시나리오마다 흩어짐
    return real_send(...)
```

**좋은 패턴 (이 프로젝트)**:
```python
# runner.py — 단 한 곳만 wrap
with safe_mode.intercept():
    case04.run(...)

# core/messaging/discord.py — 외부 호출 함수
def send(content, webhook_url):
    # 시나리오는 이 함수를 그대로 호출
    requests.post(webhook_url, json={"content": content})

# safe_mode.intercept()가 unittest.mock.patch로 send를 가로챔
```

> "이 원칙 없으면 시나리오 50개에 if DEMO_SAFE 50번 흩뿌려져 있고, 한 군데 빠뜨리면 시연 중 진짜 메시지가 외부로 나갑니다."

### E.2 모듈 참조 호출 컨벤션

**나쁨**:
```python
from core.ai.client import chat  # 함수 직접 import
chat(...)  # safe_mode.patch가 못 잡음
```

**좋음**:
```python
from core.ai import client  # 모듈 import
client.chat(...)  # safe_mode.patch가 client.chat을 잡음
```

> "patch는 namespace를 바꾸는 거라 함수 직접 import하면 namespace 다른 데 가서 못 잡습니다. 모듈 참조 호출이 컨벤션."

### E.3 column_map 강제 — 재사용성의 핵심

엑셀 모듈은 column_map 인자를 **필수**로 받습니다 (default 없음).

```python
# 나쁨 (하드코딩)
def read_vendors(folder):
    df = pd.read_excel(f"{folder}/jan.xlsx")
    return df["거래처명"], df["매출액"]  # ← 컬럼명 하드코딩

# 좋음 (column_map 강제)
def read_vendors(folder, column_map: dict[str, str]):
    df = pd.read_excel(f"{folder}/jan.xlsx")
    df = df.rename(columns={v: k for k, v in column_map.items()})
    return df["vendor"], df["amount"]  # ← 표준화 키
```

> "이 컨벤션 덕분에 다른 회사 가도 column_map 매핑만 바꾸면 코드 변경 0줄."

### E.4 OpenRouter 폴백 체인

`core/ai/client.py::MODEL_PRIORITY`:

```python
MODEL_PRIORITY = [
    "google/gemini-2.5-flash",       # Primary: 저렴 + 빠름
    "anthropic/claude-haiku-4.5",    # 2차 fallback
    "openai/gpt-4o-mini",            # 3차 fallback
]

def chat(messages, **kwargs) -> str:
    if safe_mode.is_safe():
        return force_safe()  # DEMO_SAFE + no key → 캐시 응답

    for model in MODEL_PRIORITY:
        try:
            return _call(model, messages, **kwargs)
        except (RateLimitError, APIStatusError):
            continue
    return force_safe()  # 모든 모델 실패 → 캐시 응답
```

> "이 4단계가 시연 안정성의 비밀. 모델 한 개 503 나도 자동 폴백, 4개 다 죽어도 캐시 응답."

### E.5 secrets 마스킹 — 로그에서 자동 제거

```python
# core/common/secrets_mask.py
PATTERNS = [
    re.compile(r"sk-or-v1-[a-zA-Z0-9]{40,}"),  # OpenRouter
    re.compile(r"https://discord.com/api/webhooks/\d+/[a-zA-Z0-9_-]+"),  # Discord
    re.compile(r"[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+:\S+"),  # SMTP user:pass
]

def mask(text: str) -> str:
    for pattern in PATTERNS:
        text = pattern.sub("<MASKED>", text)
    return text
```

> "로그·콘솔 출력에 secrets 새는 일이 보안 사고의 30%. 자동 마스킹으로 원천 차단."

### E.6 Timer — before/after 시간 비교 출력

```python
# core/common/timer.py
class Timer:
    def __init__(self, name: str, before_minutes: int = 0):
        self.name = name
        self.before_seconds = before_minutes * 60
        self.start = None

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *_):
        elapsed = time.perf_counter() - self.start
        ratio = self.before_seconds / elapsed if elapsed > 0 else "∞"
        print(f"{self.name}: before {self.before_seconds // 60}m → after {elapsed:.1f}s (~{ratio:.0f}배)")
```

```python
# 시나리오에서 사용
with Timer("거래처별 월별 매출 보고서", before_minutes=180):
    case01.run(...)
# → "거래처별 월별 매출 보고서: before 180m → after 5.2s (~2076배)"
```

> "이 출력 한 줄이 강의의 핵심 메시지. 자동화 효과를 청중이 1초만에 이해."

---

## 부록 F — 강의 후 follow-up 이메일 템플릿

청중에게 강의 끝나고 보낼 이메일 (워크숍 신청 유도).

```
제목: AX 사무자동화 60분 강의 follow-up — 워크숍 신청 안내

안녕하세요 [이름]님,

오늘 AX 사무자동화 60분 강의에 참여해주셔서 감사합니다.
오늘 보여드린 10개 케이스 중에서 [이름]님 회사 업무에 매핑되는 영역이 있으셨다면,
1:1 워크숍에서 본격 도입 시뮬레이션 진행드립니다.

[워크숍 진행 단계]
- W1 (1주차): 업무 매핑 + 우선 도입 케이스 1~2개 선정
- W2 (2주차): 사용 환경 데이터 5~10건 hold-out 검증
- W3 (3주차): 1주 PoC + 운영자 트레이닝
- W4 (4주차): 도입 결정 + 유지보수 계약

[참고 자료]
- 케이스 시연 대본 10개: docs/demo_scripts/
- Phase 2 plan v2: specs/2026-05-01-phase2-plan.md
- 페르소나: personas/company.md, characters.md

[워크숍 신청]
- 이메일: hyunil8702@gmail.com
- 일정 협의: [Calendly 또는 워크숍 신청 링크]

감사합니다.
```

---

## 부록 G — 정직성 체크리스트 (R3-H1 강의용)

이 강의에서 **하지 말아야 할 말**:

- [ ] "100% 정확합니다" — 정확도 단언 금지. "충분합니다 / hold-out 검증 권장"으로 표현
- [ ] "ChatGPT 대신 이걸 쓰세요" — ChatGPT를 부정하는 게 아니라 **다른 영역**임을 강조
- [ ] "도입 후 사고 0건입니다" — 사고 사례 있으면 그대로 공개. 이번 시연은 가상 데이터 기반
- [ ] "다른 회사도 똑같이 됩니다" — 회사마다 환경 다름. 도입 사이클 1~4주 솔직히 명시
- [ ] "가격은 최저가입니다" — 가격 비교는 객관적 사실로만. 비용 cherry-picking 금지

이 강의에서 **꼭 해야 할 말**:

- [ ] 시연 데이터가 합성 데이터임을 인트로 또는 OCR 블록에서 명시
- [ ] case06 한글 미설치 노트북 시연 불가 사실 명시
- [ ] case10 음성 입력은 Phase 3 사실 명시
- [ ] rhwp PoC 실패 사실 명시 (질문 들어오면)
- [ ] hold-out 검증 권장 (도입 전 필수)
- [ ] 카카오톡 자동발송 금지 사실 (case04 블록에서)

> R3-H1 정직성은 컨설팅 신뢰의 기반. "다 잘된다"보다 "이런 한계 있다"고 정직하게 말하는 발표가 컨설팅 계약 더 잘 따냅니다.

---

## 부록 H — 강의 진행 중 자기 점검 (강사용)

20분 단위로 자기 점검:

### [0:20] 첫 점검 — Excel + Messaging 절반 끝났을 때

- [ ] 청중 반응: 고개 끄덕임 보였는가?
- [ ] 페이스: 케이스당 5분 ±30초 안에 끝났는가?
- [ ] 시연 안정성: Discord 알림 정상, 콘솔 출력 정상?
- [ ] 다음 블록 점검: case03 Gmail 환경변수 OK?

### [0:40] 중간 점검 — Docgen + OCR 끝났을 때

- [ ] case06 한글 GUI 결과 시각 확인 했는가?
- [ ] case07 Ollama 응답 속도 정상 (영수증당 ~600ms)?
- [ ] 청중 질문 폭주 시작했는가? → Q&A까지 미루기
- [ ] 시간 체크: 40분 ±2분이면 정상. 45분 넘으면 case10 압축 준비

### [0:55] 마무리 점검 — Q&A 진입

- [ ] case10 owner hallucinate 방지 메시지 전달 했는가?
- [ ] Q&A 첫 질문 강사가 던질 준비 (보안·hold-out 검증)
- [ ] 워크숍 신청 안내 슬라이드 띄울 준비
- [ ] 명함·QR코드 스크린 띄울 준비

---

— 끝 —
