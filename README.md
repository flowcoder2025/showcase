# AX Showcase

사무자동화 쇼케이스 — 고객 미팅·강의 시연 + 다음 컨설팅 프로젝트에서 import해 재사용할 코어 라이브러리.

## Setup

```bash
uv sync
cp .env.example .env  # API 키 입력
```

## Usage

```bash
# 메뉴 모드 (시연용)
uv run python runner.py

# 환경 점검 (시연 전)
uv run python runner.py --check

# 시연 직전 강제 점검 (Ollama + Discord webhook ping 포함)
uv run python runner.py --check --strict

# 안전 모드 (외부 API 미호출, 캐시 응답)
DEMO_SAFE=1 uv run python runner.py case09
```

## Structure

- `core/` — 재사용 라이브러리 (CLI 무관)
  - `common/` — config, demo_logger, timer, secrets_mask, safe_mode
  - `excel/` — reader, merger, pivot, writer, validator
  - `messaging/` — discord, email (Gmail API + SMTP 폴백)
  - `docgen/` — template (Jinja2 + escape), word, pdf (npx tsx md-to-pdf), hwpx (양식 채우기), hwp_preview (Phase 3 placeholder)
  - `ocr/` — gemma (Ollama Gemma 4 wrapper), receipt, invoice
  - `ai/` — client (OpenRouter + 폴백 체인), prompts, tasks
- `cases/` — 얇은 시나리오 wrapper (case01~case10)
- `personas/` — AX상사 가상 회사·인물·시드 데이터 (영수증 100장, 세금계산서 30장, 회의록 5건 등)
- `docs/` — 시연 대본 (1/3/5분 × 8 케이스) + 강의 노트 (60분)
- `tests/` — 회귀 + DoD + integration (507 passed, 3 skipped)
- `specs/` — 설계 문서, Phase plan, deviation 결정 문서
- `memory/` — 프로젝트 상태·세션 로그 (mem-resume 진입점)

자세한 설계: `/Volumes/포터블/AX/기획/specs/ax-showcase/2026-04-30-design.md`
Phase 2 plan: `specs/2026-05-01-phase2-plan.md`

## 케이스 라인업 (10/10 시연 가능)

| # | 카테고리 | 제목 | 페르소나 |
|---|---------|------|---------|
| case01 | excel | 거래처별 월별 매출 보고서 자동 생성 | 박과장 |
| case02 | excel | 거래명세서 단가 검증 + Discord 이상치 알림 | 최주임 |
| case03 | messaging | 견적 메일 일괄 발송 (개인화 + PDF 첨부) | 이대리 |
| case04 | messaging | 미수금 단계별 Discord 알림 (사내 채널) | 박과장 |
| case05 | docgen | 견적서/거래명세서 자동 생성 (Word·PDF) | 이대리 |
| case06 | docgen | 정부지원사업 신청서 HWPX 양식 (한글 GUI 수동 확인) | 김사장 |
| case07 | ocr | 영수증 일괄 OCR → 경비 정리 엑셀 (Gemma 4 E2B) | 박과장 |
| case08 | ocr | 거래명세서·세금계산서 OCR + CSV export (Gemma 4 E4B) | 박과장 |
| case09 | ai | 거래처 응대 메일 AI 초안 (사내 톤 + 거래 이력, 3안) | 이대리 |
| case10 | ai | 회의록 텍스트 → 요약 + 액션아이템 + 담당자 자동 배정 | 김사장 |

## 시연 추천 조합

- **고객 미팅 5분**: case01 + case04 + case09 (엑셀 + Discord + AI)
- **고객 미팅 10분**: case01 + case03 + case07 + case09 + case10
- **강의 60분**: 10개 전부, 카테고리당 2개씩 (`docs/lecture_notes/60min.md`)

## Phase 1 — 완료

Foundation + 코어 인터페이스 검증 (case01/02/09).

- 통과 항목: column_map 재사용, OpenRouter 폴백 체인, safe_mode 단일 경계, secrets 마스킹, deterministic safe 캐시
- 종료 시점: 83 passed, ruff/mypy clean
- 종료 commit: `95fea4f` (T18 cleanup)

## Phase 2 — 완료 (2026-05-02 종료)

case03~10 양산 + DoD 검증 + 3-reviewer audit + cleanup. **이 README는 Phase 2 close commit (T26) 시점 상태를 반영**한다.

### 실측치 (Phase 2 종료)

| 항목 | 값 | 측정 명령 |
|------|---|----------|
| 테스트 | **507 passed, 3 skipped** | `uv run pytest -q` |
| Phase 2 신규 테스트 | 424 (= 507 − Phase 1 baseline 83) | — |
| Production lock (mypy --strict) | **52 source files clean** | `uv run mypy --strict core/ runner.py cases/` |
| Tests 부채 (mypy --strict) | **65 errors in 8 files** (Phase 1 legacy, ceiling locked) | `uv run mypy --strict tests/` |
| Lint | clean | `uv run ruff check .` |
| Format | 102 files already formatted | `uv run ruff format --check .` |
| 시연 가능 케이스 | **10 / 10** | — |
| Phase 2 audit cleanup HEAD | `b4e4628` (T25) | `git log --oneline` |

> **Cumulative file count semantics** (R1-M2): "production lock"은 `mypy --strict core/ runner.py cases/` 결과 (52 files). "tests/ 부채"는 `mypy --strict tests/` 결과 (65 errors / 8 files, ceiling). 향후 cumulative count 보고 시 어느 측정인지 명시할 것.

### Phase 2 핵심 변경 (Group 단위 요약)

- **Group A — case04 (Discord 단계별 미수금)**: `discord.send_with_level` 단일 patch point + 마스킹/429/empty body 가드
- **Group B — case05 (docgen Word/PDF)**: `docgen/template.py` Jinja2 + `docgen/word.py build_quote` + `docgen/pdf.py md_to_pdf` (npx tsx 경로)
- **Group C — case03 (이메일 일괄 + PDF 첨부)**: `messaging/email.py` Gmail API primary + SMTP 폴백, multipart + attachment, secrets_mask Gmail/SMTP 패턴 추가
- **Group D — case07 (영수증 OCR Gemma 4 E2B)**: `ocr/gemma.py` client-side timeout + jsonschema 재시도, `ocr/receipt.py` ReceiptData TypedDict, 100장 영수증 시드 (3.1MB 노이즈 적용)
- **Group E — case10 (회의록 AI)**: `ai/tasks.summarize_meeting` ActionItem/MeetingSummary TypedDict, owner hallucinate 방지 (attendees ground truth 강제), whisper deferral 결정
- **Group F — case08 (세금계산서 OCR Gemma 4 E4B)**: `ocr/invoice.py` 사업자번호 modulus 검증 + 회계 CSV export (cp949/utf-8 dual encoding)
- **Group G — case06 (HWPX 정부지원사업)**: `core/docgen/hwpx.py` (`HwpxEditor` Python 클래스 wrapper), `core/docgen/hwp_preview.py` (Phase 3 placeholder, NotImplementedError + actionable 메시지). **rhwp PoC 5옵션 모두 실패 → 한글 GUI 수동 확인 경로** (`specs/rhwp-poc-decision.md`)
- **Group H — DoD + audit**: 60분 강의 노트, 4 카테고리별 DoD test (messaging/docgen/ocr/ai), integration DoD, 3-reviewer 병렬 audit, T25 cleanup (audit findings critical/high)

### Build order — case03 ↔ case05 swap (Plan v2 Deviation 1)

`case03`은 `case05`의 PDF 모듈에 의존하므로 **case05를 먼저 구축**한 후 case03을 진행했다. 따라서 실제 진행 순서는:

```
04 → 05 → 03 → 07 → 10 → 08 → 06
```

원래 plan 표기 `04 → 03 → 05 → 07 → 10 → 08 → 06`은 의존성 모순이었다. 자세한 근거는 `specs/2026-05-01-phase2-plan.md` Deviation 1 참조.

### 5건 Deviation (정직성 disclosure)

1. **case03 ↔ case05 swap** — PDF 첨부 의존성 정렬 (위 build order). 결정: case05 PDF 모듈 우선.
2. **rhwp PoC 실패 → Phase 3 deferred** — 5옵션 (HOP CLI, rhwp WASM/wasmtime, rhwp 로컬 HTTP, rhwp cargo from source, LibreOffice headless, kordoc) 모두 PoC budget 초과 또는 미구현. case06은 한글 GUI 수동 시각 확인. 결정 문서: `specs/rhwp-poc-decision.md`.
3. **case10 whisper deferral** — 음성 입력은 Phase 3로 연기. 텍스트 회의록 입력만 지원. `openai-whisper` ~1GB + ffmpeg 의존성, 시연 임팩트는 텍스트만으로 동등. 결정 문서: `specs/case10-whisper-decision.md`.
4. **DoD §13 N6 partially passed** — 합성 영수증 ≥90% 정확도는 검증, 실 영수증 10장 hold-out은 데이터 미확보로 Phase 3로 이관. `test_dod_n6_holdout_partially_passed_marker`가 partially-passed 라벨을 회귀 잠금. 결정 문서: `specs/dod-n6-decision.md`.
5. **weasyprint 폴백 dropped** — Pango/Cairo 시스템 의존성 OSError. T5에서 폴백 없이 raise (시연 안정성 + 단순성 우선). PDF 생성은 npx tsx md-to-pdf 단일 경로. 재검토는 Phase 3.

### 알려진 부채 (R3-H1 disclosure)

- **tests/ mypy --strict 부채**: 65 errors / 8 files (Phase 1 legacy, T25에서 ceiling 잠금). `test_test_tree_strict_debt_does_not_grow` 회귀 가드 — 부채가 늘면 실패. 점진 정리는 Phase 3 또는 별도 chore.
- **safe_mode dummy 호환 패턴 산재**: case03/04/05 시나리오가 `{"_safe": True, ...}` dict를 직접 감지 → SendResult/dict[Any] TypedDict 계약 bypass. 통일안 후보 2개 미결. (`memory/critical-gaps.md` #5)
- **`core/excel/reader.read_excel(column_map=...)` 헬퍼 부재**: case01/02/03/04/05/07이 `pd.read_excel` 직접 호출 + 시나리오 내부 column_map 적용. 헬퍼 추출 시 회귀 테스트 강화 필요. (`memory/critical-gaps.md` #6)

## Phase 3 — 진입 조건 (R1-O4)

> **Phase 2 종료 후 실 미팅 또는 강의에서 2회 이상 시연 → 피드백 반영 후 Phase 3 진입.**

External usage promise: `specs/phase2-external-usage-promise.md` (하드 마감 **2026-05-09**, 작성일 2026-05-02 기준 +7일). 미충족 시 "production-ready" 주장을 retract하고 Phase 3 게이트 차단.

### Phase 3 후보 작업 (backlog)

`specs/rhwp-poc-decision.md` + `specs/dod-n6-decision.md` + `specs/case10-whisper-decision.md` + `memory/critical-gaps.md` 통합:

- **T-PHASE3-RHWP-1** rhwp v2.0.0 (PDF 출력) prebuilt 검증 (3시간)
- **T-PHASE3-RHWP-2** HOP CLI 추가 발생 시 통합 (2시간)
- **T-PHASE3-RHWP-3** LibreOffice 24+ HWPX 필터 1일 PoC
- **T-PHASE3-OCR-1** 실 영수증/세금계산서 10장 hold-out 검증 → DoD §13 N6 fully passed 승격
- **T-PHASE3-WHISPER-1** whisper 통합 옵션 평가 (openai-whisper / OpenRouter audio / macOS Speech)
- **T-PHASE3-DEBT-1** safe_mode dummy 호환 패턴 통일
- **T-PHASE3-DEBT-2** `core/excel/reader.read_excel(column_map=...)` 헬퍼 추출
- **T-PHASE3-DEBT-3** tests/ mypy --strict 65 → 0
- **T-PHASE3-DEBT-4** weasyprint 또는 reportlab PDF 폴백 평가
- **T-PHASE3-DEBT-5** Phase 3 reusability cleanup — `core/common/{image_io,parse,run_summary}.py` 추출 (R2 audit M2/L2/H1)

## 핵심 규칙

1. **모듈 참조 호출**: `from core.ai import client; client.chat()` (✓), `from core.ai.client import chat` (✗) — safe_mode patch 인터셉트 위해
2. **단일 safe_mode 경계**: `runner.py`만 `safe_mode.intercept()` 호출. 시나리오/케이스는 thin wrapper, 자체 wrap 금지
3. **OpenRouter 폴백 체인**: Gemini 2.5 Flash → Claude Haiku 4.5 → GPT-4o-mini → `force_safe()`
4. **column_map 강제**: 엑셀 모듈은 column_map 인자 필수, 하드코딩 금지
5. **시연 직전 검증**: `uv run python runner.py --check --strict` (Ollama + Discord webhook ping 포함)
6. **TDD + cumulative project lock**: 각 task 신규 파일은 mypy --strict 통과해야 다음 진입
7. **subagent-driven workflow**: implementer + N.5 fixer per task, Phase 종료 시 3-reviewer 병렬 audit
8. **익명화**: 실고객 데이터 매핑은 1Password/age 외부 보관, 레포에는 `.no_real_data` sentinel만
