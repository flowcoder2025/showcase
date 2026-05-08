# AX Showcase — Phase 3 Design v2 (재사용 라이브러리 우선 + 사내 단일 user 데모)

작성: 2026-05-08
대상 HEAD: `4537919` (T29-docs — Phase 3 v1 design + plan commit)
짝 plan 문서: `specs/2026-05-08-phase3-plan-v2.md` (writing-plans 후속 작성)
참조 v1 문서: `specs/2026-05-08-phase3-design.md`, `specs/2026-05-08-phase3-plan.md` (history 보존)

## 0. v1 → v2 변경 이유

**v1 (2026-05-08 작성)**: Phase 3을 "Web 모듈화 + 코어 패키지화"로 잡되, 5개 sub-phase(3-A 리팩터 → 3-B FastAPI → 3-C Queue+Storage → 3-D Frontend → 3-E Multi-tenant)로 SaaS 방향까지 커버.

**v2 (이 문서)**: 사용자 의도 재정렬 — **재사용 목적 > 시연 목적**. 시연은 "현재 CLI로는 라이브 시연이 어렵다"를 해결할 만큼만 (사내 단일 user Streamlit). 재사용 패키지 추출 + dogfood + cross-version 풀 잠금 검증을 1순위로 끌어올림.

### 0.1 컷 (v1에서 의도적으로 제거)

| v1 단계 | 컷 사유 |
|---|---|
| 3-B FastAPI 라우트 | 단일 user 시연에 dead weight. 외부 N user 결정 시점에 추가. ScenarioResult 인터페이스 덕에 Streamlit→FastAPI swap 클린. |
| 3-C Dramatiq + Redis 큐 | 단일 process 단일 user면 OCR 직렬화는 Streamlit이 자연 보장. |
| 3-C MinIO/S3 + Postgres + Alembic | 로컬 디스크 + `run.json` (JSONL 메타)로 충분. |
| 3-D2 Next.js 정식 frontend | Streamlit MVP가 사내 단일 user에 충분. Next.js는 외부 공개 결정 시점. |
| 3-E Multi-tenant + Auth.js + 멀웨어 검사 | Non-goal 명시. |
| 외부 SaaS 출시 / 결제 / PII access log | v1과 동일 Non-goal. |

### 0.2 살림 + 강화

| 항목 | v1 위치 | v2 위치 / 변경 |
|---|---|---|
| 3-A Refactor (ScenarioResult + Backends DI + contextvars) | T29~T34 | 그대로 (v2 §3, §4, §6) |
| 패키징 P1~P3 (별도 트랙) | Phase 3-A 종료 후 어디든 | **3-Pkg로 승격 — Phase 3-A 직후 고정** (재사용이 1순위) |
| 즉시 wins W1~W3 | 병렬 트랙 | 그대로 (v2 §6) |
| Streamlit MVP 3-D1 | Phase 3-D 마지막 단계 | **3-Web으로 단순화 — FastAPI 없이 Streamlit이 cases.scenario.run() 직접 호출** (v2 §3) |
| 검증 전략 | mypy strict + pytest 회귀 0 | **풀 잠금으로 강화 — dogfood fixture + `__all__` snapshot + Python 3.11/3.12/3.13 cross-version** (v2 §5) |

## 1. Scope / Non-goals

### 1.1 Scope

- 현 `core/`을 **`packages/flowcoder-office-tools/`로 monorepo workspace 패키지 분리**. 다음 컨설팅 프로젝트가 framework-agnostic으로 import 가능 (`pip install -e packages/flowcoder-office-tools` 또는 git+ssh subdirectory dep).
- **3-A 모듈화**:
  - `cases/_protocols.py` — `ScenarioResult` TypedDict + `Backends` frozen dataclass + Protocol 정의
  - `flowcoder_office_tools.backends` — MLX/OpenRouter/Discord/Gmail/Safe/Cached 구현
  - `flowcoder_office_tools.common.safe_mode_v2` — `os.environ` → `contextvars.ContextVar` 전환
  - `cases/<id>/scenario.py::run()` 시그니처 정식화 (`input_dir`, `output_dir`, `backends`, `progress_cb`, `config` keyword-only)
- **풀 잠금 검증** (v2 §5):
  - dogfood fixture (`tests/dogfood/`) — fresh venv → `pip install` → smoke
  - `__all__` 명시 + signature snapshot + breaking change detector
  - GitHub Actions matrix Python 3.11 / 3.12 / 3.13
  - 539 + 4 skipped 회귀 0 + 신규 80+ tests
- **즉시 wins (W1~W3)**: E4B 4bit 다운로드, few-shot prompting 강화, `runner.py --warmup-blocking`
- **사내 단일 user Streamlit MVP** (`web/app.py`) — `cases.<id>.scenario.run()` 직접 import 호출

### 1.2 Non-goals (이번 Phase 3에서 제외)

- 외부 SaaS / 결제 / 멀티 테넌시 / 인증 미들웨어 / 감사 로그
- FastAPI / Dramatiq / Redis / Postgres / Alembic / MinIO / S3
- Next.js 정식 frontend / 디자인 시스템 통합
- 음성 → 텍스트 (case10 whisper deferral 그대로 — `specs/case10-whisper-decision.md`)
- HWPX 실시간 미리보기 (rhwp PoC 5옵션 실패, deferred — `specs/rhwp-poc-decision.md`)
- 자체 모델 fine-tune / 모바일 / 멀티 리전

## 2. 외부 사용 게이트 v2 재정의

### 2.1 v1 약속의 한계

`specs/phase2-external-usage-promise.md` (Phase 2 T23, 2026-05-02 작성):

> Phase 2 종료 후 실 미팅 또는 강의에서 **2회 이상** 사용 → 피드백 반영 후 Phase 3 진입.
> 하드 마감: 2026-05-09. 미충족 시 production-ready 주장 retract + Phase 3 게이트 차단.

이 약속은 v1 design의 "production-ready SaaS" 가정을 전제로 함. v2 의도(재사용 라이브러리 + 사내 단일 user 데모)에선 다음 두 이유로 게이트가 정합하지 않음:

1. v2엔 "production-ready SaaS" 주장 자체가 없음 (3-E 멀티테넌트 컷)
2. 재사용 가치 검증은 외부 미팅이 아니라 **dogfood fixture가 매 PR마다 자동 강제** — 더 강한 검증

### 2.2 v2 게이트 재정의

| 항목 | v1 게이트 | v2 게이트 |
|---|---|---|
| 검증 대상 | "production-ready SaaS" 주장 | "재사용 라이브러리 + 사내 단일 user 데모" 주장 |
| 충족 조건 (필수) | 외부 미팅·강의 2회 시연 | **(a) dogfood fixture CI 통과** — 매 PR 자동 강제 |
| 충족 조건 (실증) | (위 항목에 포함) | **(b) 실제 다음 컨설팅 프로젝트 1건이 `flowcoder-office-tools` import 통과** — 발생 시 추적표 row append (게이트 차단 없음, 실증 마커) |
| 마감 (a) | 2026-05-09 (Phase 2 종료 +7일) | Phase 3-Pkg(T38) 종료 시점 — 미충족 시 패키지 추출이 미완성이라는 의미 |
| 마감 (b) | 위와 동일 | 마감 없음 — 실 사용이 발생할 때 자연 충족. Phase 3 종료 게이트는 (a)만 |
| 미충족 시 | production-ready 주장 retract + Phase 3 차단 | (a) 미충족 시 "재사용 가능 패키지" 주장 retract (코드는 유지, "검증 진행 중" 라벨) |

### 2.3 R5 처리 — Phase 3 코드 진입 전 docs-only commit

T29 시작 직전 **`T28.5-docs(gate)` 단일 commit**:

1. `specs/phase2-external-usage-promise.md` 갱신 — v1 게이트 retract + v2 게이트 본 §2.2 내용 append
2. `README.md` Phase 2 섹션 — "production-ready SaaS" 주장 retract + Phase 3 v2 의도 명시
3. `CLAUDE.md` Phase 진행 상황 섹션 — 게이트 v2 link
4. `memory/MEMORY.md` 진행 상태 섹션 — 게이트 v2 link

코드 변경 0건. 추정 ~15분. 이후 T29 코드 진입.

## 3. Target 아키텍처

```
┌──────────────────────────────────────┐    ┌──────────────────┐
│  Streamlit (showcase/web/app.py)     │    │  runner.py (CLI) │
│  - case 선택 / 업로드 / 진행바 / 결과│    │  - 메뉴, MLX 관리│
└──────────────┬───────────────────────┘    └────────┬─────────┘
               │ direct python import                │
               └─────────────────┬───────────────────┘
                                 │
                ┌────────────────▼─────────────────┐
                │  showcase/cases/<id>/scenario.py │
                │  run(*, input_dir, output_dir,   │
                │      backends, progress_cb,      │
                │      config) -> ScenarioResult   │
                └────────────────┬─────────────────┘
                                 │ import flowcoder_office_tools as fot
                ┌────────────────▼─────────────────┐
                │  packages/flowcoder-office-tools │
                │  src/flowcoder_office_tools/     │
                │   ├─ excel/ messaging/ docgen/   │
                │   ├─ ocr/ ai/ common/            │
                │   ├─ backends/ (Protocol + impls)│
                │   └─ protocols.py (ScenarioResult│
                │                    + Backends)   │
                │  → framework-agnostic, stdlib +  │
                │    pinned deps only               │
                └────────────────┬─────────────────┘
                                 │ Backend DI
                ┌────────────────▼─────────────────┐
                │  External: mlx_vlm / OpenRouter /│
                │  Discord / Gmail (Backend impls) │
                └──────────────────────────────────┘

═══════════════════════════════════════════════════════════════════
검증 트랙 — tests/dogfood/ (CI 매 PR, 게이트 (a)):
  fresh venv
    → pip install packages/flowcoder-office-tools[ocr,messaging,docgen,ai]
    → python -m dogfood_smoke   (safe backend, 외부 호출 0)
    → 위 `packages/flowcoder-office-tools` layer 검증
```

### 3.1 Layer 책임

| Layer | 위치 | 책임 | 의존 |
|---|---|---|---|
| `flowcoder_office_tools` | `packages/flowcoder-office-tools/src/flowcoder_office_tools/` | 비즈니스 로직 (excel/messaging/docgen/ocr/ai) + Backend protocol. **framework-agnostic** (stdlib + pinned 외부 lib만). | 없음 |
| `cases.<id>.scenario` | `showcase/cases/` | 입력 → 코어 호출 → ScenarioResult. **stateless 함수만**. | `flowcoder_office_tools` |
| `runner.py` | `showcase/` | CLI launcher, 인자 파싱, 메뉴, MLX subprocess spawn, scenario 호출 | cases + fot |
| `web/app.py` (Streamlit) | `showcase/web/` | UI: 업로드, 진행바, 결과 카드. `cases.<id>.scenario.run()` 직접 호출. | cases + fot |
| dogfood fixture | `tests/dogfood/` (CI fresh venv) | 외부 프로젝트 import 시뮬레이션 | fot only |

### 3.2 핵심 설계 원칙

1. **`flowcoder_office_tools`는 cases / runner / Streamlit / 다음 컨설팅 프로젝트 4종 동일 import**. framework 의존 0.
2. **`cases`는 라이브러리의 첫 번째 consumer + integration test 베드**. 539개 테스트가 사실상 패키지 검증.
3. **`runner.py`와 Streamlit은 같은 `scenario.run()`을 호출**. UI shell만 다름. 두 launcher 회귀 0.
4. **Backend DI 주입 지점**:
   - `runner.py`: 진입 시 `default_backends()` / `safe_backends()` (DEMO_SAFE 기준)
   - Streamlit: 사이드바 토글 또는 `.env`로 결정
   - **외부 컨설팅 프로젝트**: 자체 backend (예: `AzureOpenAIBackend`) 주입 가능 — 재사용 가치의 핵심

## 4. 데이터 흐름 + 동시성 처방

### 4.1 데이터 흐름 (단일 user, 단일 process)

```
[User] ─upload─▶ [Streamlit]
                     │
                     │ runs/{run_id}/input/ 디렉토리 생성
                     ▼
                [scenario.run(
                    input_dir=runs/{id}/input,
                    output_dir=runs/{id}/output,
                    backends=resolved_backends(safe=sidebar_toggle),
                    progress_cb=streamlit_progress_adapter,
                    config={column_map, threshold, ...}
                 )]
                     │
                     │ progress_cb → st.progress + st.write
                     ▼
                [ScenarioResult]
                  ├─ summary_text   → st.success 카드
                  ├─ output_files[] → st.download_button per file
                  ├─ metrics{}      → st.dataframe (처리시간 / 성공·실패 카운트)
                  └─ failures[]     → st.warning 표 (case07 OCR 실패 12건 등)

runs/{run_id}/  (24h TTL — Streamlit 시작 시 expire한 디렉토리 cleanup)
  ├─ input/
  ├─ output/
  └─ run.json  (ScenarioResult 직렬화 — 새로고침/북마크 후에도 결과 유지)
```

### 4.2 G1~G5 중 단일 user에서 살아있는 가정 + 처방

v1 design §2.2의 5개 깨지는 CLI 가정 중 단일 user에서도 처방이 필요한 것:

| # | 가정 | 단일 user 영향 | 처방 | 비용 |
|---|---|---|---|---|
| G1 | `DEMO_SAFE` env = process-wide 토글 | 낮음 (단일 thread) | `contextvars.ContextVar` 도입 | 작음 — 미래 N user 정합성 + Streamlit script rerun 안전성 |
| G2 | `safe_mode.intercept` = `unittest.mock.patch` (process global) | 중간 (Streamlit rerun이 import 재실행) | Backends DI로 이주 | **재사용 패키지화에 필수** |
| G3 | mlx_vlm.server 단일 인스턴스 직렬 | 없음 (자연 직렬) | 처방 불요 | 0 |
| G4 | output dir cwd 기준 | 중간 (CLI + Streamlit 동시 실행 충돌) | run_id 디렉토리 격리 | 작음 |
| G5 | scenario가 `os.environ` / `Path("cases")` / `Path("personas/sample_data/...")` 직접 참조 | **높음** — 외부 프로젝트가 import 시 깨짐 | scenario.run() 시그니처 정식화 (input/output/config 인자) | **재사용 가치의 핵심** |

### 4.3 에러 처리 정책

1. **Backend 실패** → 기존 폴백 체인 유지 (`OpenRouter` 모델 폴백 → `force_safe()`)
2. **scenario 내부 실패** (한 건 OCR 실패 등) → `ScenarioResult.failures[]`에 구조화. raise는 catastrophic(파일 없음, schema 불일치 등)만.
3. **Streamlit 측 catastrophic** → `st.error()` + traceback을 `run.json`에 직렬화 (재현·디버깅용)
4. **CLI(`runner.py`)도 동일 정책** — 두 launcher 일관성

## 5. 검증 전략 (풀 잠금)

### 5.1 Dogfood fixture project

`tests/dogfood/` 안에 minimal `pyproject.toml` + smoke 스크립트 (~30줄):

```
fresh venv → pip install ./packages/flowcoder-office-tools[ocr,messaging,docgen,ai]
          → pip install ./tests/dogfood
          → python -m dogfood_smoke
```

smoke 스크립트:
- 모든 public API import (`from flowcoder_office_tools.excel import read_excel`, ...)
- 핵심 함수 1회 호출 (safe backend 강제, 외부 호출 0건)
- `ScenarioResult` 형태 검증 (TypedDict 필드 5종 모두 존재)

다른 프로젝트가 `pip install`해서 import할 때의 환경을 정확히 재현 — 다음 컨설팅 프로젝트의 첫 import는 dogfood가 이미 통과한 길.

### 5.2 `__all__` lock + breaking change detector

각 public 모듈에 `__all__` 명시:

```python
# flowcoder_office_tools/excel/__init__.py
__all__ = ["read_excel", "merge_files", "build_pivot", "write_workbook", "validate_columns"]
```

`tests/test_public_api_surface.py`:
- `__all__` 모든 심볼 import 통과
- public 함수 signature snapshot (`inspect.signature` 직렬화) → `tests/snapshots/public_api.json`과 비교
- snapshot 변경 시 → 테스트 실패 → PR description에 **BREAKING CHANGE: ...** 강제 (수동 confirm 후 snapshot 갱신 commit)

### 5.3 Cross-version smoke (Python 3.11 / 3.12 / 3.13)

GitHub Actions matrix:
- 3.11: full pytest (539+4 + 신규)
- 3.12 / 3.13: dogfood smoke + `__all__` import만 (시간 절약, 외부 lib 호환성만 검증)

신규 의존성 추가 시 자동 cross-version 호환 catch — 다음 프로젝트가 3.12/3.13이어도 안심.

### 5.4 회귀 0 + 신규 테스트

| 항목 | T28 baseline (cf76f50) | Phase 3 종료 expected |
|---|---|---|
| pytest | 539 passed + 4 skipped | **620+** (Backends 30+, contextvars 10+, scenario sigchg 회귀 보강 20+, dogfood ~10, public API surface 5+, Streamlit smoke 5+) |
| mypy --strict source files | 53 | **70+** (`packages/flowcoder-office-tools/src/`, `web/app.py` 추가) |
| ruff check / format --check | clean | clean |
| 시연 가능 case | 10/10 (CLI) | 10/10 (CLI + Streamlit) |
| e2e smoke | runner.py 4건 | runner + Streamlit 4건 |

### 5.5 검증 게이트 매핑

| 검증 항목 | local | CI | 실패 시 |
|---|---|---|---|
| pytest 539+4 회귀 0 | 매 commit | 매 push | merge block |
| 신규 backends/contextvars/scenario tests | 매 commit | 매 push | merge block |
| dogfood smoke (fresh venv) | optional | 매 PR | merge block |
| `__all__` surface snapshot | 매 commit | 매 push | snapshot 변경 시 PR description gate |
| cross-version (3.12 / 3.13) smoke | optional | 매 PR | merge block |
| ruff check + format --check | 매 commit | 매 push | merge block |
| mypy --strict (cumulative lock) | 매 commit | 매 push | merge block |
| 3-reviewer audit (R1 보안 / R2 아키 / R3 정직성) | — | Phase 3 종료 시 (T43) | critical 0건 / high는 fixer commit |

**핵심 약속**: 이 4축 통과한 패키지는 **다른 프로젝트의 빈 venv에 `pip install`하면 그대로 동작**. dogfood fixture가 매 PR마다 자동 증명.

## 6. Task Map + 추정 + Risks

### 6.1 Task Map

```
T28.5 docs(gate)              ── 외부 사용 게이트 v2 재정의 (15분, 코드 0)
   ↓
3-A Refactor (T29~T34)        ──┐
                                │ 즉시 wins (W1~W3) 병렬 진행
3-Pkg Extraction (T35~T38)    ──┤
                                │
3-Web Streamlit MVP (T39~T42) ──┘
   ↓
Phase 3 close (T43~T44)
```

### 6.2 Task 분해

| ID | 작업 | 산출물 | 추정 |
|---|---|---|---|
| **T28.5** | docs-only — 외부 사용 게이트 v2 재정의 + production-ready SaaS 주장 retract | `specs/phase2-external-usage-promise.md` 갱신 + README/CLAUDE/MEMORY 정합화 | ~15분 |
| **T29** | `cases/_protocols.py` — ScenarioResult TypedDict + Backends frozen dataclass + Protocol 정의 | 신규 1 file (mypy 53→54) | 0.5d |
| **T30** | `core/backends/` — MLX/OpenRouter/Discord/Gmail/Safe/Cached 구현 + 30+ tests | 신규 1 dir + tests | 1d |
| **T31** | `core/common/safe_mode_v2.py` — contextvars 기반 + 기존 safe_mode shim | 신규 1 file + tests | 0.5d |
| **T32** | case01~case10 scenario 시그니처 정식화 + runner.py 디폴트 채움 | 10 scenarios + runner | 1.5d |
| **T33** | progress_cb 표준화 + CLI rich.progress 어댑터 | runner 헬퍼 + cases 루프 | 0.5d |
| **T34** | Phase 3-A 통합 검증 (mypy/pytest/ruff full) | 회귀 0 증빙 | 0.5d |
| **T35** | `packages/flowcoder-office-tools/` scaffold — pyproject + workspace dep + showcase pyproject 갱신 | 신규 dir + 양쪽 pyproject | 0.5d |
| **T36** | `core/` → `packages/.../src/flowcoder_office_tools/` 이주 (shim 단계 — 양쪽 import 공존) | move + shim | 1d |
| **T37** | `__all__` 명시 + `tests/test_public_api_surface.py` + signature snapshot baseline | 신규 1 test + snapshot json | 0.5d |
| **T38** | `tests/dogfood/` fixture + CI matrix (3.11/3.12/3.13) + shim 제거 | 신규 dir + .github/workflows 갱신 | 0.5d |
| **T39** | `web/app.py` 골격 — 10 case 카드 메뉴 | 신규 1 file | 0.5d |
| **T40** | 입력 업로드 + run_id 디렉토리 격리 + scenario.run() 직접 호출 | web/app.py 확장 | 1d |
| **T41** | progress_cb → st.progress 어댑터 + 결과 카드 (download/summary/metrics/failures 표) | web/app.py 마무리 | 0.5d |
| **T42** | Phase 3-Web 통합 검증 + Streamlit smoke test | 신규 e2e test | 0.5d |
| **T43** | 3-reviewer audit (R1 보안 / R2 아키 / R3 정직성) | findings 정리 | 0.5d |
| **T44** | Phase 3 close — README/CLAUDE/MEMORY 갱신 + 외부 사용 추적표 update + Phase 4 backlog | docs commit | 0.5d |
| **W1** | E4B 4bit 다운로드 + symlink (병렬, 사용자 환경) | symlink 갱신 | 0.5d |
| **W2** | Few-shot prompting 강화 (`core.ocr.gemma._default_prompt`) | prompt 수정 + 100장 검증 | 0.5d |
| **W3** | `runner.py --warmup-blocking` | runner 옵션 추가 | 0.25d |

**추정 합계**: ~10.5일 (W는 3-A와 병렬 → 실 wallclock ~10일).

### 6.3 Risks

| # | Risk | 처방 |
|---|---|---|
| R1 | 패키지 분리 시 import path 변경으로 모든 case 깨짐 | T36 shim 단계 (양쪽 import 공존) + `libcst` codemod로 자동화. 마이그레이션 commit은 import path만 변경 (semantic 0) |
| R2 | dogfood fixture가 mlx_vlm.server 외부 의존 | dogfood smoke는 **safe backend 강제** — 외부 호출 0건 통과 (`SafeBackend(*)` 주입) |
| R3 | `__all__` snapshot이 너무 엄격 → 일반 리팩터도 PR block | T37 baseline은 현재 public 표면 그대로. **BREAKING CHANGE만 차단**. 신규 추가는 자유 |
| R4 | Streamlit rerun 모델이 import-time mutation에 취약 | Backends DI로 모든 외부 의존 함수 인자화 (T30 핵심) |
| R5 | 외부 사용 게이트 0/2 + 하드 마감 2026-05-09 | T28.5 docs commit으로 게이트 v2 재정의 + production-ready SaaS 주장 retract 동시 진행 (§2.3) |
| R6 | `safe_mode_v2` shim 기간이 길어지면 두 모드 공존 부채 | T34 통합 검증 시점에 monkey patch 의존 테스트 모두 마이그레이션. shim은 Phase 3-Pkg(T38) 종료 시점에 제거. |
| R7 | Streamlit의 `st.session_state` 활용 vs 함수 stateless 원칙 충돌 | UI state는 Streamlit, 비즈니스 state는 `run.json` (디스크). scenario.run()은 stateless 유지. |
| R8 | dogfood fixture가 mlx_vlm.server / discord webhook 등 환경 의존성에서 깨짐 | dogfood는 safe backend만 사용. 환경 의존 검증은 `runner.py --check --strict`이 담당 (별도 트랙). |

## 7. 결정 미루기 (Phase 4 후보 — v1과 동일)

- 자체 모델 fine-tune (영수증 카테고리 분류기, 한국어 OCR 정확도 향상)
- 사내 vector DB + RAG (회의록/제안서 사내 룰 자동 적용)
- whisper 통합 (case10 deferred decision matrix per `specs/case10-whisper-decision.md`)
- HWPX 실시간 미리보기 재평가 (rhwp 후속 또는 LibreOffice headless)
- 모바일 (사진 업로드 → 영수증 OCR) — 사내 영업 직원용
- **외부 N user 결정 시점에 추가**: FastAPI 라우트, Dramatiq 큐, MinIO/S3, Postgres, Auth.js — v1 design 문서의 §5~§7 그대로 reference

## 8. 외부 사용 시나리오 (v2 재정의)

v1 §13의 시나리오는 v2 게이트 재정의에 따라 다음 두 채널로 대체:

### 8.1 dogfood fixture (자동, 매 PR — 게이트 (a) 강제)

- T38 시점에 활성화. CI에서 fresh venv → `pip install` → smoke 통과 = 게이트 (a) 매 PR 자동 충족.
- T38 종료 후 본 게이트 (a)는 영구히 PR merge 차단 조건으로 작동. 회귀 시 즉시 catch.

### 8.2 다음 컨설팅 프로젝트 import 사용 (수동, 발생 시점 — 게이트 (b) 실증 마커)

- `packages/flowcoder-office-tools`을 git+ssh subdirectory dep으로 추가
- 첫 import + 첫 함수 호출 통과 시 `specs/phase2-external-usage-promise.md` 추적표에 row append (일자/프로젝트명/import한 모듈/관찰)
- (b)는 게이트 차단 없음. Phase 3 종료 자체는 (a)로만 결정. (b)는 실제 외부 사용이 일어났다는 실증 기록.

### 8.3 사내 단일 user 시연 (Streamlit MVP)

- T42 종료 후 본인이 사내 미팅·강의에서 Streamlit MVP 시연
- 게이트와 무관 (게이트 v2는 import 검증 중심) — 단 시연 중 발견되는 UX 이슈는 별도 backlog

## 9. Glossary

- **DI** — Dependency Injection. 현 monkey patch 대체.
- **dogfood fixture** — 다른 프로젝트가 패키지를 import하는 환경을 재현하는 CI 단계.
- **G1~G5** — v1 design §2.2의 5개 깨지는 CLI 가정. v2 §4.2에서 단일 user에 살아있는 것만 추림.
- **G2 처방 = Backends DI** — `safe_mode.intercept` (monkey patch) 대신 `Backends` 인스턴스를 함수 인자로 주입.
- **monorepo workspace dep** — 단일 git repo 안에서 패키지를 분리하되, pyproject가 `packages/foo` 디렉토리를 dependency로 참조하는 방식.
- **public API surface** — `__all__`로 노출된 심볼 + signature. 변경 시 BREAKING CHANGE 라벨 강제.
- **ScenarioResult** — 모든 case scenario.run()의 표준 반환 TypedDict (case_id / summary_text / output_files / metrics / failures).
- **shim 단계** — `core/`와 `packages/.../flowcoder_office_tools/` 둘 다 import 가능한 마이그레이션 임시 단계 (T36~T38).
- **Streamlit MVP** — FastAPI 없이 Streamlit이 직접 cases.scenario.run()을 호출하는 단일 process 사내 시연 도구.
- **W1~W3** — 즉시 wins. E4B 4bit / few-shot / warmup-blocking. 3-A와 병렬 가능.

## 10. 변경 이력

- 2026-05-08 v1: Phase 3 design 초안 (5 sub-phase, SaaS 방향까지 커버). HEAD `4537919`. 작성자: Claude Opus 4.7.
- 2026-05-08 v2 (이 문서): 사용자 의도 재정렬 (재사용 우선 + 사내 단일 user 데모). FastAPI/Queue/DB/Multi-tenant 컷, 패키지화 1순위 승격, 풀 잠금 검증 추가. 짝 plan은 writing-plans 스킬로 후속 작성.
