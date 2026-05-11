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

## 진행 상태 (2026-05-11 시점) — **Phase 3-A ✅ 종료 + Phase 3-Pkg T42 ✅ (scaffold)**

- **HEAD**: `7d55a58` (T42 — packages/flowcoder-office-tools/ scaffold + uv workspace)
- **테스트**: **668 passed, 4 skipped** (Phase 2 baseline 539 + Phase 3-A·정합·Pkg-scaffold 신규 129, 회귀 0)
- **Production lock (mypy --strict)**: `core/ + runner.py + cases/` **65 source files clean** (53 → 65, +12). packages/는 T43 이주 후 strict scope 편입 예정
- **tests/ 부채 (mypy --strict)**: **103 errors / 13 files** — T41.5 시점 ceiling 잠금 (`tests/test_test_tree_strict_debt_does_not_grow.py`). Phase 2 close 65/8 → T41 직전 107/16 (+42/+8 무방어 누적), T41.5 신규 4 errors fix → 103/13 lock
- **ruff**: clean (`ruff check .` + `ruff format --check .`)
- **시연 가능**: 10/10 (case07/08 e2e 검증 유지 — T28 MLX 백엔드)

### Phase 3-A T35~T41 완료 (2026-05-10 → 05-11, 8 commits)

| Task | Commit | Source | Tests | mypy strict | 비고 |
|------|--------|--------|-------|-------------|------|
| T34.5 docs(gate) | `a91d351` | promise.md gate 정직 정정 (마감 도과 인정) | — | — | docs |
| T35 protocols | `22e921a` | `cases/_protocols.py` (ScenarioResult + 3 Protocol + serialize_result + as_display) | +37 | 53→54 | |
| T36 backends | `4b2f2ae` | `core/backends/` 9 파일 (MLX/OpenRouter/Discord/Gmail/Safe/Cached×3/Factory) | +46 | 54→63 | |
| T37 safe_mode_v2 | `3420436` | `core/common/safe_mode_v2.py` (ContextVar sentinel + force_safe Token) + shim | +8 | 63→64 | |
| T38 scenarios | `dffe360` | 10 scenario.run keyword-only ScenarioResult + runner + 16 test codemod + 10 smoke | +10 | 64→65 | |
| T39 cwd-coupling | `61f4a31` | safe_mode.cache_path 절대화 + AX_CACHE_DIR/AX_CASES_DIR env override | +12 | 65 | G5 검증 |
| T40 progress | `3b11c75` | step/done/emit + rich_progress_adapter context manager + 5 case 발행 + runner.py wire | +12 | 65 | R2-H3 |
| T41 통합 검증 | `bdd1489` | safe_mode_v2 8→10 보강 + 통합 verification | +2 | 65 | R3-H1 |

**Phase 3-A 핵심 설계 결정 (구현 완료)**:
- ScenarioResult TypedDict 6 필드 (`case_id`/`summary_text`/`output_files`/`metrics`/`failures`/`extras`)
- Backend Protocol DI (OCR/AI/Messaging) + `Backends` frozen dataclass + factory.py
- safe_mode v2 ContextVar 기반 (env mutation 0, R1-H3) — sentinel pattern으로 env-fallback 호환
- 10 scenario `run(*, input_dir, output_dir, backends, progress_cb, config) -> ScenarioResult`
- 절대 경로 default + env override (`AX_CACHE_DIR`, `AX_CASES_DIR`) — G5 cwd-independence
- case06 `template_path`, case09 `incoming_message`은 `config[...]`로 전달
- ProgressEvent (TypedDict) + step/done/emit + rich_progress_adapter (context manager)

### T41.5~T42 — 정합 + Phase 3-Pkg 진입 (2026-05-11 추가, 3 commits)

**T41.5** `1a36885` — 전체 완성도 체크에서 발견된 stale fact 3건 정정:
- mypy strict 신규 부채 4 errors fix (test_backends_safe / test_case10_signature / test_g5)
- ceiling lock test 재구현 (`tests/test_test_tree_strict_debt_does_not_grow.py`) — 103 errors / 13 files lock
- MEMORY.md / critical-gaps.md 갱신 (T39~T41 완료 반영)

**T41.6** `b65732d` — critical-gaps §1 해결 (force_safe Token leak 차단):
- `safe_mode.intercept(case_id, apis)` 가 entry-time `is_safe()` 값을 `safe_mode_v2.safe_mode_scope` 로 lock
- gemma/client/email 의 force_safe(token discard) 패턴 그대로 보존 — within-case sticky failover 의도 유지
- cross-case leak 만 boundary 가 자동 복원 → 회귀 차단 test 추가 (`test_intercept_boundary_isolates_force_safe_between_cases`)
- 핵심 교훈: "caller-controlled scope ≠ caller가 token reset" — boundary가 책임지는 게 더 안전 (lessons.md 추가)

**T42** `7d55a58` — Phase 3-Pkg 진입 (scaffold + uv workspace):
- `packages/flowcoder-office-tools/` 디렉토리 + pyproject.toml (hatchling, optional deps: ocr/messaging/docgen/ai)
- `__version__ = "0.1.0a1"` + README (alpha 상태)
- root pyproject: `[tool.uv.workspace]` + `[tool.uv.sources]` + dependencies 등록
- 검증: `uv pip show` editable from packages/.../src ✓, `import flowcoder_office_tools` ✓, 회귀 0
- Plan deviation 2건 (정직): requires-python `<3.14` → `>=3.11` (Python 3.14.4 차단 회피), license="Proprietary" 라인 제거 (SPDX 표준 외 hatchling parse 실패)

### 외부 사용 게이트 (T34.5 정직 정정 후)

- **하드 마감 2026-05-09 도과**. 0/1 미충족 인정 — 약속은 보존.
- production-ready 라벨 retracted (T32). Phase 3 진입 결정 = 옵션 (a) — 사내 데모 + dogfood만 게이트로 운용.
- 향후 외부 시연 시 `specs/phase2-external-usage-promise.md` 추적표에 row append → `partially-fulfilled (1+/?)` 갱신.

---

## 진행 상태 (2026-05-02 시점) — **Phase 2 ✅ 완료 (T0~T26, Group A~H 종료)**

- **Phase 2: T0~T26 전체 완료, 8개 Group 종료** ✅
- 테스트: **507 passed, 3 skipped** (Phase 1 baseline 83 + Phase 2 신규 424, 회귀 0)
- Lint/format: ruff clean (check + format)
- Production lock (mypy --strict): `core/ + runner.py + cases/` **52 source files clean**
- tests/ 부채 (mypy --strict): **65 errors / 8 files** (Phase 1 legacy, ceiling 명시적 lock 부재 — T41.5에서 103/13 으로 갱신 + lock test 재구현)
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

- **외부 사용 약속**: `specs/phase2-external-usage-promise.md` (T32 정정 — 2026-05-08)
  - 현재 충족: 0/1 (약속 자체는 보존)
  - **production-ready 라벨 retracted** (T32 commit). Phase 3 의도가 design v2.1(commit `b5ffe0f`)에서 "재사용 라이브러리 + 사내 단일 user 데모"로 재정렬.
  - 외부 사용 (1)은 보존 + dogfood (2)는 추가 검증 (대체 아님). 둘 다 v2.1 §2.2 게이트.
  - 충족 시 promise 파일 추적표에 일자/청중/시연 케이스/관찰 row append.

### Phase 2 commits / deviations / lessons (요약)

전체 Phase 2 commit history는 `git log` (T0~T26, 2026-05-01~05-02). 핵심 deviation 5건 + lessons은 `lessons.md` 참조.

### Cumulative project lock 추적

각 task 신규 파일은 mypy --strict 통과해야 다음 진입. **현재 (T38 종료)**: **65 source files clean** (core/ + runner.py + cases/). tests/ 누적 부채는 scope 외.

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

## Phase 3 설계 + 플랜 (2026-05-08, v1 → v2 → v2.1 self-revise 후 audit 정정 완료)

- v1: `specs/2026-05-08-phase3-design.md` + `2026-05-08-phase3-plan.md` (history 보존, SaaS 방향)
- v2: 사용자 의도 재정렬로 재사용 우선 + 사내 단일 user 데모로 응축
- **v2.1 (active)**: `specs/2026-05-08-phase3-design-v2.md` (commit `b5ffe0f`, T31). 3-reviewer audit 17건 finding 반영. 핵심:
  - 게이트 v2.1: (1) 외부 사용 약속 보존 + (2) dogfood 추가 검증 (대체 아님)
  - 추정 정직 정정: ~10.5d → ~12.5d (T37/T38 분해, T42/T43 분해)
  - framing 정정: "풀 잠금" → "다층 잠금 (3.11 풀 + 3.12/3.13 smoke)"
  - 보안 minimum: ScenarioResult sanitizer + Streamlit 127.0.0.1 + path traversal 방어
- **진입 절차**: T32 retract-only commit (이번 세션) → T33 게이트 정합화 → T34부터 코드 진입

## 다음 세션 진입 (Phase 3-Pkg T43 진입)

```bash
cd /Users/jerome/AX/showcase && claude
/mem-resume
git log --oneline -10                      # HEAD 7d55a58 (T42) 확인
uv run pytest -q                           # 668 passed, 4 skipped
uv run mypy --strict core/ runner.py cases/   # 65 source files clean
uv run python -c "import flowcoder_office_tools; print(flowcoder_office_tools.__version__)"  # 0.1.0a1 (T42 scaffold)
grep -n "^### T43" specs/2026-05-08-phase3-plan-v2.md  # T43 spec (line 1321)
```

**즉시 진입 가능**: T43 (`core/` → `packages/.../src/flowcoder_office_tools/` 이주). plan v2.1.1 line 1321~. 큰 작업이라 단계 분할 권장:
- (a) `scripts/migrate_imports.py` (libcst codemod, ImportFrom + Import + SimpleString) 작성 + dry-run 검증
- (b) 모듈 이주 (`core/{common,excel,messaging,docgen,ocr,ai,backends}`, `core/progress.py`, `cases/_protocols.py`)
- (c) string-based monkeypatch / patch 13+건 변환 (사전 grep 필수)
- (d) `core/__init__.py` shim with `__getattr__` lazy forward (R2-M2)
- (e) 회귀 0 + mypy strict + ruff clean

### Phase 3-Pkg 진행 순서 (남은 task)

- **T43**: `core/` → packages 이주 + libcst codemod + 13+ string mock 변환
- **T44**: `core/` shim (`__getattr__` lazy forward) + 외부 import 안정 contract 선언
- **T45**: dogfood fixture: showcase 가 packages 만으로 동작하는지 CI 검증
- **T46**: Phase 3-Pkg close + dogfood CI 통과 시 외부 사용 게이트 (b) 충족

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
