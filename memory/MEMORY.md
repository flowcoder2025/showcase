---
name: AX Showcase 사무자동화 케이스 쇼케이스
description: 고객 미팅·강의 시연용 사무자동화 케이스 10건 + 실전 재사용 코어 모듈 라이브러리
type: project
originSessionId: 5f17504f-aeae-4369-a83b-4a0ef76e757b
---
# AX Showcase

사무자동화 케이스를 모듈 단위로 정리해 (1) 고객 미팅·강의 라이브 시연, (2) 다음 컨설팅 프로젝트에서 import해 재사용하는 두 목표를 동시에 달성하는 프로젝트.

**Why**: AX 컨설팅 미팅·강의에서 "이런 거 됩니다" 보여줄 임팩트 자산이 부족했고, 매 컨설팅마다 같은 엑셀·메일·OCR 모듈을 새로 짜는 비효율을 끊기 위함.

**How to apply**: AX 컨설팅·제안 작업 중 사무자동화 시연이 필요할 때 또는 다음 프로젝트에서 엑셀/메일/OCR/AI 모듈이 필요할 때 이 레포의 `core/`를 import. 진행 상태·다음 단계는 아래 참조.

## Locations

- **Code repo**: `/Volumes/포터블/AX/showcase/` (별도 git repo, fresh repo from 2026-04-30)
- **Spec (v2.1)**: `/Volumes/포터블/AX/기획/specs/ax-showcase/2026-04-30-design.md`
- **Phase 1 plan**: `/Volumes/포터블/AX/기획/specs/ax-showcase/2026-04-30-phase1-plan.md` (17 tasks / 104 steps)

## 핵심 결정사항

- **카테고리 5개**: 엑셀, 메시징, 문서생성, OCR, AI
- **케이스 10개**: 카테고리당 2건, 그중 1건은 본인 실고객(콩코드/번영에프씨/온고롱) 영감 익명화
- **앵커 회사**: 가상 "AX상사" — 제조·유통 겸업 중소기업, 직원 30~50명 (김사장/박과장/이대리/최주임)
- **아키텍처**: Layered — `core/`(CLI 무관 라이브러리) + `cases/`(얇은 시나리오 wrapper) + `personas/`(가상 데이터 시드). 추후 webapp 확장은 wrapper만 추가
- **스택**: Python 3.11+ / uv / pandas / openpyxl / OpenRouter (openai SDK 호환) / Ollama (Gemma 4 — Phase 2) / discord-webhook / rich / pytest / ruff
- **HWP**: `hwpx-editor` 스킬 = 양식 채우기, **rhwp** (Rust+WASM, MIT) = 미리보기 렌더 (case06 진입 전 PoC 1일 의무)
- **OCR**: Gemma 4 E2B/E4B (Ollama 로컬, 2026-04-02 릴리스) — PaddleOCR 대체
- **카카오 자동발송 금지** (약관·스팸법) → 케이스 04는 **Discord webhook** (사내 채널 알림)

## 안정성 장치

- `core/common/safe_mode.py` — `unittest.mock.patch` 기반 외부 호출 인터셉트 + sha1 캐시 + 자동 폴백 (`force_safe`)
- 외부 호출은 **모듈 참조로 호출** 컨벤션: `from core.ai import client; client.chat()` (✓), `from core.ai.client import chat` (✗)
- `core/common/secrets_mask.py` — Discord webhook URL / OpenRouter 키 자동 마스킹
- `core/ai/client.py` `MODEL_PRIORITY` 폴백: Gemini 2.5 Flash → Claude Haiku 4.5 → GPT-4o-mini → `force_safe()`
- `runner.py --check --strict` (시연 직전 필수), `runner.py --safe` (외부 API 미호출, 캐시 응답)
- 익명화 매핑은 1Password 또는 `age` 암호화로 외부 보관 — 레포에는 `.no_real_data` sentinel만

## Phase 분할

- **Phase 1** (1~1.5주): Foundation + 케이스 3건 (case01 엑셀 보고서 / case02 단가검증+Discord / case09 AI 메일 초안) — 코어 인터페이스(column_map·safe_mode·OpenRouter 폴백·patch 격리·secrets 마스킹) 조기 검증
- **Phase 2** (2~3주): 나머지 7개 케이스 (case03~08, case10) — 진행 순서 04→03→05→07→10→08→06
- **Phase 3** (선택): 회귀 테스트 자동화 + webapp(Streamlit/FastAPI 그때 결정) + `core/` 사내 패키지(`flowcoder-office-tools`) 분리

## 진행 상태 (2026-05-02 시점) — **Phase 2 ✅ 완료 (T0~T26, Group A~H 종료)**

- **Phase 2: T0~T26 전체 완료, 8개 Group 종료** ✅
- 테스트: **507 passed, 3 skipped** (Phase 1 baseline 83 + Phase 2 신규 424, 회귀 0)
- Lint/format: ruff clean (check + format)
- Production lock (mypy --strict): `core/ + runner.py + cases/` **52 source files clean**
- tests/ 부채 (mypy --strict): **65 errors / 8 files** (Phase 1 legacy, ceiling locked by `test_test_tree_strict_debt_does_not_grow`)
- **HEAD (Phase 2 audit cleanup)**: `b4e4628` (T25). T26은 docs-only close commit (README/CLAUDE/MEMORY 갱신).
- **시연 가능**: case01~case10 **10/10**
- 진행 순서 (Plan v2 Deviation 1 swap 반영): **04 → 05 → 03 → 07 → 10 → 08 → 06** (case03이 case05 PDF 모듈에 의존)
- 진행 방식: subagent dispatch (implementer + N.5 fixer per task) + Phase 종료 시 3-reviewer 병렬 audit + audit findings cleanup. 모든 verification 출력 commit body 첨부 강제 (R3-H1 정직성).

### Phase 2 종료 5건 deviation (정직성 disclosure)

1. **case03 ↔ case05 swap** — PDF 첨부 의존성 정렬 (case05 PDF 먼저 → case03이 사용)
2. **rhwp PoC 5옵션 모두 실패 → Phase 3 deferred** (`specs/rhwp-poc-decision.md`). case06은 한글 GUI 수동 시각 확인.
3. **case10 whisper deferral** (`specs/case10-whisper-decision.md`). Phase 2는 텍스트 입력만.
4. **DoD §13 N6 partially passed** (`specs/dod-n6-decision.md`). 실 영수증 10장 hold-out → Phase 3.
5. **weasyprint 폴백 dropped** — Pango/Cairo 의존성 OSError. md-to-pdf (npx tsx)만 사용, 실패 시 raise.

### Phase 3 진입 조건 (R1-O4)

> Phase 2 종료 후 실 미팅 또는 강의에서 **2회 이상** 사용 → 피드백 반영 후 Phase 3 진입.

- **외부 사용 약속**: `specs/phase2-external-usage-promise.md`
  - 현재 충족: 0/2
  - 하드 마감: **2026-05-09** (작성일 +7일). 미충족 시 production-ready 주장 retract + Phase 3 게이트 차단.
  - 충족 시 promise 파일 추적표에 일자/청중/시연 케이스/관찰 row append.

### Phase 2 핵심 commits (T0~T13, 2026-05-01~05-02)

**T0 prep** (`653c386`): lxml/Gmail-SMTP env vars, runner `_check_email_transport`, anonymization_policy.md

**Group A — case04 (Discord 단계별 미수금)**
- T1 (`3b5e6cd`) / T1.5 (`5e7f655`): `discord.send_with_level` 단일 patch point + 마스킹/429/empty body
- T2 (`307ed4f`): case04 시나리오 + vendors 시드 재사용 (60건 24/18/12/6 분포)

**Group B — case05 (docgen Word/PDF)**
- T3 (`640549e`) / T3.5 (`d63e69d`): `docgen/template.py` Jinja2 + `render_html_string` (XSS 방어)
- T4 (`d6f3b76`) / T4.5 (`f73bbb5`): `docgen/word.py build_quote` + 한글 폰트 명시
- T5 (`c791400`) / T5.5 (`4ba3223`): `docgen/pdf.py md_to_pdf` (npx tsx) + `MdToPdfError`
- T6 (`f7c175a`) / T6.5 (`f219f8e`): case05 시나리오 (10 requests, 42 rows)

**Group C — case03 (이메일 일괄 + PDF 첨부)**
- T7a (`d6608a6`) / T7a.5 (`11dcccf`): `email.build_message` multipart + 첨부 + XSS escape helper
- T7b (`2ef84ed`) / T7b.5 (`d3c470b`): `email.send` Gmail API + SMTP 폴백, secrets_mask Gmail/SMTP 패턴
- T8 (`54499bd`) / T8.5 (`b984917`): case03 시나리오 50건 + pdf_failed counter

**Group D — case07 (영수증 OCR Gemma 4 E2B)**
- T9 (`656d0a1`) / T9.5 (`f415a41`): `ocr/gemma.py` client-side timeout + jsonschema validation/retry
- T10 (`51749d5`) / T10.5 (`a7de79e`): `ocr/receipt.py` ReceiptData TypedDict + 날짜/금액 정규화
- T11 (`487748e`) / T11.5 (`94935bd`): case07 시나리오 + 100장 영수증 시드 (3.1MB 노이즈 적용) + payment 추출

**Group E — case10 (회의록 AI)**
- T12 (`c7d6748`) / T12.5 (`7ceded1`): `ai/tasks.summarize_meeting` + ActionItem/MeetingSummary TypedDict + owner hallucinate 방지
- T13 (`87b5cde`): case10 시나리오 + 5 회의록 시드 + whisper deferral 결정 문서

**Group F — case08 (세금계산서 OCR Gemma 4 E4B)**
- T14 (`8be229e`) / T14.5 (`7f2f532`): `core/ocr/invoice.py` 사업자번호 modulus 검증 + 회계 CSV export (BOM option + biznum format diversity)
- T15 (`fc681ab`) / T15.5 (`89b372f`): case08 시나리오 + 30 세금계산서 시드 (validation threshold + column override)

**Group G — case06 (HWPX 정부지원사업)**
- T16 (`7f156f8`): `core/docgen/hwp_preview.py` placeholder + `specs/rhwp-poc-decision.md` (5옵션 평가 후 Phase 3 deferred) + hwpx-editor python import smoke
- T17 (`5764005`): `core/docgen/hwpx.py` Python `HwpxEditor` wrapper (sys.path.insert pattern)
- T18 (`ecf70a6`): case06 HWPX 정부지원사업 양식 시나리오 + 한글 GUI 수동 시각 확인 경로

**Group H — DoD + audit + close**
- T19 (`5cbee7c`): 60분 강의 노트 (10 케이스 통합 1시간 강의 대본)
- T20 (`471c503`): DoD messaging (case03/04 verification)
- T21 (`f476a7c`): DoD docgen (case05/06 verification)
- T22 (`690142d`): DoD ocr (case07/08 verification + N6 hold-out partially-passed marker, `specs/dod-n6-decision.md`)
- T23 (`4e75d6e`): DoD ai + integration verification + `specs/phase2-external-usage-promise.md`
- T24: 3-reviewer 병렬 audit (R1/R2/R3 findings)
- T25 (`b4e4628`): Phase 2 audit findings cleanup (critical + high)
- T26 (this commit): README + CLAUDE + MEMORY Phase 3 gate finalize (docs-only)

### Plan v2 + 3-reviewer audit (2026-05-01)

`specs/2026-05-01-phase2-plan.md` (2075줄) — 3-reviewer audit 5건 critical 정정:
- R3-C1 md-to-pdf 경로 hallucination → `npx tsx scripts/md-to-pdf.ts` 정정 (실측)
- R3-C2 client.chat 시그니처 → `-> str` + `json.loads` 정정
- R3-C3 hwpx-editor 호출 → Python `HwpxEditor` `sys.path.insert` 정정
- R1-C1 discord intercept 단일 patch point
- R3-H1 모든 task verification에 `ruff format --check` 명시 + N.5 reviewer 체크리스트

### Spec deviation 5건
1. **case03 ↔ case05 swap** (PDF 의존성 정렬)
2. **rhwp PoC fallback** (실패 시 Quick Look)
3. **case10 whisper deferral** → Phase 3 (`specs/case10-whisper-decision.md`)
4. **DoD §13 N6 hold-out** → 실 영수증 10장 미확보 시 partially passed 라벨 (T22)
5. **weasyprint 보류** (T0 발견) → Pango/Cairo 의존성 OSError, T5에서 폴백 없이 raise

### 핵심 commits (T9~T18, 2026-05-01 후속 세션)
- T9: `dbd6687` (prompts + tasks) → T9.5: `f91da39` (lint/type)
- T10: `2232dd5` (discord webhook) → T10.5: `3ebe460` (TypedDict + override)
- T11: `1b678f4` (personas + Faker) → T11.5: `171a189` (relativedelta — 30-day drift 버그 수정)
- T12: `3aa67f9` (runner.py) → T12.5: `59a71f7` (types-PyYAML + annotations)
- T13: `cb61e93` (case01 vendor report) → T13.5: `1714c7a` (annotations + ws guard)
- T14: `5cca8fb` (case02 invoice + discord) → T14.5: `f2312ba` (thin-wrapper 복원 + LOO docstring + types)
- T15: `43fca91` (case09 AI mail) → T15.5: `0c18f1e` (chat() safe-mode short-circuit — 자체 보호)
- T16: `c436ec7` (시연 대본 1/3/5분 × 3 케이스 + rehearsal_log)
- T17: `d6841ec` (DoD test 8건) + `17aa69e` (README Phase 1 close) → T17.5: `43bc053` (test annotations)
- **T18 cleanup (3-reviewer audit 후속)**:
  - `fa56294`: C1-C4 + S1 — assert→ValueError, openai 타입 예외, yaml try/except, test_case09 강화 (deterministic 실증), writer "vendor" 하드코딩 제거
  - `bc39344`: S2-S9 — merger 컬럼 strict, datetime errors=raise, tasks.draft_email warning log, runner --check --strict (Ollama+Discord ping), config.load 통합 (load_dotenv 단일경로), UTF-8 명시, auto-open mtime 필터, test_critical_imports_smoke hasattr 강화
  - `95fea4f`: ruff format . 일괄 적용 (35 파일 reformat)

### 발견된 spec 버그 / 아키텍처 정정
- **T11.5**: `timedelta(days=30 * offset)` → `relativedelta(months=offset)` (12개월 12파일 보장)
- **T14**: `validator.detect_unit_price_outliers` 그룹 z-score → leave-one-out z-score (verbatim 알고리즘은 outlier가 std inflate해 boundary miss)
- **T14.5**: scenario 자체 `safe_mode.intercept` wrap 제거 → "thin wrapper" 아키텍처 복원 (runner.py가 sole intercept boundary)
- **T15.5**: `core/ai/client.py::chat`이 `safe_mode.is_safe()` 미체크 → DEMO_SAFE=1 + no API key 시 401 → chat() 시작부에 short-circuit 추가
- **T12/T13/T14/T15/T17 공통**: spec의 `from core.common.logging import demo_logger` → `from core.common.demo_logger import demo_logger` (T4 rename 결과)

### Phase 1 검증 인프라 교훈 (이번 세션 추가)
- subagent들이 `which mypy` (homebrew)와 `uv run which mypy` (`.venv/bin`)을 혼동해 보고 → 실제 검증은 `uv run`을 통하면 정상이지만 리포트 경로 표기는 sloppy
- 이전 교훈 유효: `uv pip list | grep mypy` + `uv run which mypy`로 `.venv/bin/` 항상 확인

### Cumulative project lock 추적
- T8 종료: 10 files (core/ 일부)
- T17.5 종료: 40 files (`core/` 21 + `runner.py` + `cases/` 3개 + `tests/` 12개 신규)
- T18 종료: **40 files 유지 + ruff format 전체 적용 + 추가 robustness** (test 강화로 사실상 quality는 향상되나 file count는 동일)
- 정책: 각 task 신규 파일은 mypy --strict 통과해야 다음 진입. 기존 test 파일들의 누적 부채(73 errors in 9 files)는 scope 외 — Phase 2 별도 정리 가능.

### T18에서 발견·정정된 이슈 (3-reviewer audit)
- **C1**: `writer.py` `assert nlevels==1` → `raise ValueError` (`-O` strip 안전성)
- **C2**: `client._call` 문자열 매칭 → `openai.RateLimitError`/`APIStatusError` 타입 분류
- **C3**: `runner.discover_cases` `yaml.safe_load` 예외 처리
- **C4**: `test_case09_safe_mode_returns_deterministic_result` 약한 검증 → 실제 deterministic 실증 (text1 == text2 + content)
- **C5**: `ruff format` 35 파일 미정렬 baseline → 일괄 정렬
- **S1-S9**: writer "vendor" 하드코딩, merger 컬럼 strict, datetime errors=raise, tasks 워닝 로그, runner --check --strict (Ollama+Discord), config.load 통합, UTF-8 명시, auto-open mtime, hasattr 강화
- **새로 발견**: `config.load()`가 이전엔 `load_dotenv` 호출 안 했음 → 통합하면서 test_config 1건 환경변수 격리 추가 필요했음

### T18 deviation (정직성 기록)
- S5 Discord webhook ping: spec은 HEAD 요청이지만 Discord webhook이 405 반환 → GET으로 변경 (200/204 검증 기준은 동일)
- S5 Ollama 검증: `startswith("gemma4")` 매칭 (warmup 코드와 동일 패턴)
- Group D test fix 별도 commit 불필요 — C1 1줄 (`AssertionError` → `ValueError`)은 source change와 같이 묶음

## T27/T28 (2026-05-08, Maintenance — Phase 2 외 트랙)

- T27 `c3428e2`: case10 whisper deferral 결정 문서 복원 (`specs/case10-whisper-decision.md` 정식 등록)
- T28 `cf76f50`: Ollama → MLX(mlx_vlm.server OpenAI-호환) 백엔드 전환 + 좀비 0 보장
  - `core/ocr/_mlx_server.py` (subprocess + atexit/SIGTERM/SIGINT/SIGHUP cleanup)
  - `core/ocr/gemma.py` (openai SDK + base64 vision + 코드펜스 strip)
  - 두 인스턴스 분리 (E2B 11437, E4B 11438), `AX_OCR_BASE_URL_*` 외부 모드 공존
  - `deploy/launchd/*.plist` 옵션 + `.env.example` 신규 스키마
  - **e2e 검증**: case07 88/100 (E2B, 210s), case08 28/30 (E4B bf16, 262s), 좀비 회수 OK
  - 539 passed + 4 skipped, mypy strict 53 source files clean

## Phase 3 설계 + 플랜 (2026-05-08 작성 완료, 코드 진입 전)

- `specs/2026-05-08-phase3-design.md`: 깨지는 5개 CLI 가정 G1~G5, target 아키, layer 책임, 비기능 요구
- `specs/2026-05-08-phase3-plan.md`: T29~T52 task map (3-A Refactor → 3-B FastAPI → 3-C Queue+Storage → 3-D Frontend → 3-E Multi-tenant), 즉시 wins W1~W3, 패키징 P1~P3
- **진입 절차**: 외부 사용 ≥2/2 충족 또는 production-ready 주장 retract 후 T29부터

## 다음 세션 진입 (Phase 3-A 또는 외부 사용)

```bash
cd /Users/jerome/AX/showcase && claude
/mem-resume
git log --oneline -5                      # HEAD cf76f50 (T28) 확인
uv run pytest -q                          # 539 passed, 4 skipped
uv run python runner.py --check --strict  # 시연 환경 점검 (MLX 두 모델)
cat specs/2026-05-08-phase3-plan.md       # task map + 다음 명령 ★
```

### 진입 경로 분기

1. **외부 사용 (우선 — Phase 3 게이트)**
   - 실제 미팅·강의에서 시연 → `specs/phase2-external-usage-promise.md` 추적표에 row append (일자/청중/케이스/관찰)
   - 2회 이상 충족 + 피드백 수집 → Phase 3 진입 가능
   - 하드 마감: 2026-05-09. 미충족 시 production-ready 주장 retract.

2. **다음 컨설팅 프로젝트에서 core/ 라이브러리 import**
   - `core/{common,excel,messaging,docgen,ocr,ai}` 모두 재사용 가능
   - 모듈 참조 호출 컨벤션 유지 (`from core.ai import client; client.chat()`)
   - safe_mode 단일 경계 (`runner.py`만 intercept) 유지

3. **Phase 3 backlog (외부 사용 충족 후)**
   - T-PHASE3-RHWP-1/2/3 (rhwp v2 prebuilt / HOP CLI / LibreOffice 24+)
   - T-PHASE3-OCR-1 (실 영수증·세금계산서 10장 hold-out)
   - T-PHASE3-WHISPER-1 (whisper 통합 옵션 평가)
   - T-PHASE3-DEBT-1..5 (safe_mode dummy 통일, excel reader 헬퍼, tests/ mypy 부채, weasyprint/reportlab 평가, common util 추출)
   - 자세한 backlog: `README.md` Phase 3 섹션

## 시연 추천 조합

- **고객 미팅 5분**: case01 + case04 + case09 (엑셀+디스코드+AI)
- **고객 미팅 10분**: case01 + case03 + case07 + case09 + case10
- **강의 60분**: 10개 전부, 카테고리당 2개씩

## 케이스 10개 라인업

| # | 카테고리 | 제목 | 페르소나 |
|---|---------|------|---------|
| case01 | excel | 거래처별 월별 매출 보고서 자동 생성 | 박과장 |
| case02 | excel | 거래명세서 단가 검증 + Discord 이상치 알림 | 최주임 |
| case03 | messaging | 견적 메일 일괄 발송 (개인화 + PDF 첨부) | 이대리 |
| case04 | messaging | 미수금 단계별 Discord 알림 (사내 채널) | 박과장 |
| case05 | docgen | 견적서/거래명세서 자동 생성 (Word·PDF) | 이대리 |
| case06 | docgen | 정부지원사업 신청서 HWPX 양식 (rhwp 미리보기) | 김사장 |
| case07 | ocr | 영수증 일괄 OCR → 경비 정리 엑셀 (Gemma 4 E2B) | 박과장 |
| case08 | ocr | 거래명세서·세금계산서 OCR + CSV export (Gemma 4 E4B) | 박과장 |
| case09 | ai | 거래처 응대 메일 AI 초안 (사내 톤+거래 이력, 3안) | 이대리 |
| case10 | ai | 회의록 음성 → 요약 + 액션아이템 + 담당자 자동 배정 | 김사장 |

## 비스코프 (명시 제외)

- 웹크롤링·모니터링, ERP/CRM 직접 연동, KPI 대시보드, 영상·슬라이드 마케팅 자산
- 카카오톡 자동발송 (약관 리스크), 홈택스/회계SW 직접 연동 (CSV export까지만), HWPX 무에서 생성
