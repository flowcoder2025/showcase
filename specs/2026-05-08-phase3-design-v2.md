# AX Showcase — Phase 3 Design v2.1 (재사용 라이브러리 우선 + 사내 단일 user 데모)

작성: 2026-05-08
대상 HEAD: `acb8cb8` (T30-docs(design) — Phase 3 v2 commit; v2.1은 본 파일 in-place 갱신 commit으로 별도 hash 부여)
짝 plan 문서: `specs/2026-05-08-phase3-plan-v2.md` (writing-plans 후속 작성)
참조 v1 문서: `specs/2026-05-08-phase3-design.md`, `specs/2026-05-08-phase3-plan.md` (history 보존)

## 0. v1 → v2 → v2.1 변경 이유

### 0.0 design 작업 maturity 정직 disclose

v1과 v2는 **같은 날(2026-05-08) 같은 세션에서** 작성되었다. v1은 brainstorming-skill 선행 없이 작성된 결과로, 사용자 의도(재사용 우선 + 사내 단일 user)를 충분히 잡지 못한 채 SaaS 방향까지 커버하려 했다. v2는 brainstorming 후 의도 재정렬로 작성되었으나, **v1 plan에서 task 추정을 그대로 reuse**하는 등 self-revise 한계가 남았다. v2.1(이 갱신)은 3-reviewer audit (R1 보안 / R2 아키 / R3 정직성)에서 발견된 17건 finding을 반영한 정정이다.

**Lesson** (memory/lessons.md에 별도 기록 예정): non-trivial design은 brainstorming 선행. self-revise 1회로 끝나지 않으며 외부 reviewer가 framing 거짓을 catch하는 단계가 필수.

### 0.1 컷 (v1에서 의도적으로 제거)

| v1 단계 | 컷 사유 | 미래 swap 비용 disclose |
|---|---|---|
| 3-B FastAPI 라우트 | 단일 user 시연에 dead weight | progress_cb event interface 호환 시 ~2-3d 추가 (R2-H3 처방으로 비용 최소화) |
| 3-C Dramatiq + Redis 큐 | 단일 process 단일 user면 OCR 직렬화는 Streamlit이 자연 보장 | ~1-2d (Backends DI 덕에 actor 주입만) |
| 3-C MinIO/S3 + Postgres + Alembic | 로컬 디스크 + `run.json` (JSONL 메타)로 충분 | ~3-4d (객체 스토리지 + DB 마이그레이션) |
| 3-D2 Next.js 정식 frontend | Streamlit MVP가 사내 단일 user에 충분 | ~1주 (별도 설계 필요) |
| 3-E Multi-tenant + Auth.js + 멀웨어 검사 | Non-goal | 외부 공개 결정 시점에 별도 design |
| v1 T44 TTL 정리 cron actor | Phase 4 deferred | v2.1에서 startup + lazy cleanup으로 minimum 처방 (§4.1) |

### 0.2 살림 + 강화

| 항목 | v1 위치 | v2.1 위치 / 변경 |
|---|---|---|
| 3-A Refactor (ScenarioResult + Backends DI + contextvars) | T29~T34 | 그대로 + 책임 분리 명시 (§4.2) |
| 패키징 P1~P3 (별도 트랙) | Phase 3-A 종료 후 어디든 | **3-Pkg로 승격, T35~T39 (T38/T39 분리)** |
| 즉시 wins W1~W3 | 병렬 트랙 | 그대로 (§6) |
| Streamlit MVP | Phase 3-D 마지막 | **3-Web으로 단순화, FastAPI 없이 직접 호출** + minimum 보안 요건 명시 (§4.1) |
| 검증 전략 | mypy + pytest 회귀 0 | **다층 잠금**: dogfood + `__all__` snapshot + 3.11 풀 + 3.12/3.13 smoke |

### 0.3 v2 → v2.1 audit findings 반영 요약

3-reviewer audit (R1/R2/R3) 결과 17건(C 9 + H 9 + M 8 + L 9):

- **R1 보안 critical 3건** (C1 sanitizer / C2 Streamlit listen+path / C3 underscore export)
- **R2 아키 critical 3건** (C1 TTL owner / C2 책임 중복 / C3 ScenarioResult universality)
- **R3 정직성 critical 3건** (C1 게이트 회피 / C2 추정 베끼기 / C3 풀 잠금 framing)

각 finding은 본문 §1~§6 정정 + §부록 A 추가로 흡수. 미흡수 항목은 Phase 3 진행 중 incremental 처리 (예: R3-L1 lessons 기록, R3-M3 plan v2 hash 참조).

## 1. Scope / Non-goals

### 1.1 Scope

- 현 `core/`을 **`packages/flowcoder-office-tools/`로 monorepo workspace 패키지 분리**. **uv workspace** (`tool.uv.workspace.members = ["packages/flowcoder-office-tools"]`) + showcase pyproject가 path dep로 참조 (R2-H1 lock).
- **3-A 모듈화**:
  - `cases/_protocols.py` — `ScenarioResult` TypedDict + `extras: dict[str, Any]` 자유 영역 + `Backends` frozen dataclass + Backend Protocol (audit log contract 포함)
  - `serialize_result(r)` 단일 진입점 — `secrets_mask` 자동 적용 (R1-C1 처방)
  - `flowcoder_office_tools.backends` — MLX/OpenRouter/Discord/Gmail/Safe/Cached 구현 (cache key sha256 + backend fingerprint)
  - `flowcoder_office_tools.common.safe_mode_v2` — `contextvars.ContextVar` 전환 + **`force_safe`도 ContextVar set** (`os.environ` mutation 제거, R1-H3)
  - `cases/<id>/scenario.py::run()` 시그니처 정식화 (`input_dir`, `output_dir`, `backends`, `progress_cb`, `config` keyword-only)
  - **G5 처방 별도 line item** — `Path("personas/sample_data/...")` / `Path("cases/.../output")` 직접 참조 9건 제거 (T32에서 분해, R3-C2)
- **다층 잠금 검증** (v2.1 §5):
  - dogfood fixture (`tests/dogfood/`) — fresh venv → `pip install` → smoke (fake backend 주입 검증 포함)
  - `__all__` 명시 + signature snapshot + breaking change detector (`_`-prefix 자동 제외, R1-C3)
  - GitHub Actions matrix: **Python 3.11 풀 pytest** + 3.12 / 3.13 smoke + import만
  - 539 + 4 skipped 회귀 0 + 신규 80+ tests
- **즉시 wins (W1~W3)**: E4B 4bit 다운로드, few-shot prompting 강화, `runner.py --warmup-blocking`
- **사내 단일 user Streamlit MVP** (`web/app.py`) — `cases.<id>.scenario.run()` 직접 import 호출 + **minimum 보안 요건** (127.0.0.1 default, path traversal 방어, size cap; §4.1)

### 1.2 Non-goals (이번 Phase 3에서 제외)

- 외부 SaaS / 결제 / 멀티 테넌시 / 인증 미들웨어 / 감사 로그
- FastAPI / Dramatiq / Redis / Postgres / Alembic / MinIO / S3
- Next.js 정식 frontend / 디자인 시스템 통합
- 음성 → 텍스트 (case10 whisper deferral 그대로 — `specs/case10-whisper-decision.md`)
- HWPX 실시간 미리보기 (rhwp PoC 5옵션 실패, deferred — `specs/rhwp-poc-decision.md`)
- 자체 모델 fine-tune / 모바일 / 멀티 리전

## 2. 외부 사용 게이트 — 정직 정정 (R3-C1)

### 2.1 v1 약속의 본래 우려 (정직 재기술)

`specs/phase2-external-usage-promise.md` (Phase 2 T23, **2026-05-02 작성**, v1 design보다 6일 먼저)에 적시된 우려는:

> 3-reviewer audit R1-C2 — Phase 2 종료 후 1주 안에 실 미팅·강의에서 1회 이상 시연하지 않으면 **"production-ready" 주장이 reviewer feedback 사용처 없이 self-validation으로 끝난다는 위험**.

본래 우려는 "production-ready SaaS"라는 좁은 표현이 아니라 **외부 reviewer feedback 부재 → self-validation 위험**이라는 일반 명제. v2가 "v1 SaaS 주장과 정합 안 함"으로 게이트를 약화시킨 framing은 R3 audit에서 **straw man + after-the-fact reframe**으로 catch됨. 정정한다.

### 2.2 v2.1 게이트 (외부 사용 약속을 보존하면서 dogfood를 추가 검증으로)

| 항목 | v1 게이트 | v2.1 게이트 |
|---|---|---|
| **외부 reviewer feedback** (본래 우려 직접 대응) | 외부 미팅·강의 2회 시연 | **유지** — 외부 reviewer 부재 우려는 dogfood로 해결 안 됨. 자기 코드가 자기 코드를 import할 뿐. |
| 충족 조건 (필수, v1 보존) | 외부 미팅·강의 2회 시연 | (1) 외부 미팅·강의 1회 이상 시연 + 관찰 row append |
| 충족 조건 (추가 검증) | — | (2) dogfood fixture CI 통과 — 매 PR 자동 강제 (재사용 가능성 코드로 증명) |
| 마감 (1) | 2026-05-09 (Phase 2 종료 +7일) | **유지** — 마감 도래 시 미충족 line으로 솔직 인정 (별도 retract commit) |
| 마감 (2) | — | Phase 3-Pkg(T38) 종료 시점 |
| 미충족 시 (1) | production-ready 주장 retract + Phase 3 차단 | **외부 reviewer feedback 미수집 인정 + production-ready 라벨 retract** (별도 commit). Phase 3 코드 진입은 retract 후에만. |
| 미충족 시 (2) | — | "재사용 가능 패키지" 주장 retract |

핵심 차이: dogfood는 **추가 검증**이지 **외부 사용 약속의 대체가 아님**. v1 약속은 그대로 유지된다.

### 2.3 R5 처리 (v2.1 정정 — 두 commit으로 분리, R3-H2)

| Commit | 내용 | 추정 |
|---|---|---|
| **T32** | retract-only — 외부 사용 0/2 미충족 정직 인정 + production-ready 라벨 retract | ~20분 |
| **T33** | v2.1 게이트 정의 정합화 — `promise.md` 갱신 + README + CLAUDE + MEMORY 4 파일 cross-link | ~25분 |

이 두 commit은 코드 변경 0. 그 후 T34부터 코드 진입.

## 3. Target 아키텍처

```
┌──────────────────────────────────────┐    ┌──────────────────┐
│  Streamlit (showcase/web/app.py)     │    │  runner.py (CLI) │
│  - case 선택 / 업로드 / 진행바 / 결과│    │  - 메뉴, MLX 관리│
│  - 127.0.0.1 default + path 검증     │    │                  │
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
                │   ├─ protocols.py (ScenarioResult│
                │   │                + Backends    │
                │   │                + serialize_  │
                │   │                  result())   │
                │   └─ common/safe_mode_v2.py      │
                │  → framework-agnostic, stdlib +  │
                │    pinned deps only (uv.lock)    │
                └────────────────┬─────────────────┘
                                 │ Backend DI (audit log contract)
                ┌────────────────▼─────────────────┐
                │  External: mlx_vlm / OpenRouter /│
                │  Discord / Gmail (Backend impls) │
                └──────────────────────────────────┘

═══════════════════════════════════════════════════════════════════
검증 트랙 — tests/dogfood/ (CI 매 PR, 게이트 (2)):
  fresh venv (secret env 차단)
    → uv pip install --frozen ./packages/flowcoder-office-tools[ocr,messaging,docgen,ai]
    → python -m dogfood_smoke   (FakeBackend 주입 검증 + safe backend 동작)
    → 위 `packages/flowcoder-office-tools` layer 검증
```

### 3.1 Layer 책임

| Layer | 위치 | 책임 | 의존 |
|---|---|---|---|
| `flowcoder_office_tools` | `packages/flowcoder-office-tools/src/flowcoder_office_tools/` | 비즈니스 로직 + Backend protocol + serialize_result. **framework-agnostic** (stdlib + pinned 외부 lib만). | 없음 |
| `cases.<id>.scenario` | `showcase/cases/` | 입력 → 코어 호출 → ScenarioResult. **stateless 함수만**. | `flowcoder_office_tools` |
| `runner.py` | `showcase/` | CLI launcher, 인자 파싱, 메뉴, MLX subprocess spawn, scenario 호출 | cases + fot |
| `web/app.py` (Streamlit) | `showcase/web/` | UI: 업로드, 진행바, 결과 카드. `cases.<id>.scenario.run()` 직접 호출. **minimum 보안 요건** (§4.1). | cases + fot |
| dogfood fixture | `tests/dogfood/` (CI fresh venv) | 외부 프로젝트 import 시뮬레이션 + FakeBackend 주입 검증 | fot only |

### 3.2 Backend Protocol audit log contract (R1-H1 처방)

`Backend` Protocol에 다음 contract 명시:

```python
class Backend(Protocol):
    """All backend calls MUST log via demo_logger (auto secrets_mask).
    Custom backends bypassing demo_logger MUST apply secrets_mask.mask_text
    to args/results before any logger.

    Tested by tests/test_backend_contract_logging.py:
    sentinel secret 주입 → backend 호출 → capsys로 leak 0건 검증.
    """
```

이 contract는 docstring + `tests/test_backend_contract_logging.py`로 강제. 외부 컨설팅 프로젝트가 자체 backend (예: 가상 `AzureOpenAIBackend` — **본 design은 예시 inspirational, 실제 구현은 외부 프로젝트 책임**) 주입 시 contract 위반은 자체 테스트가 catch.

### 3.3 핵심 설계 원칙

1. **`flowcoder_office_tools`는 cases / runner / Streamlit / 다음 컨설팅 프로젝트 4종 동일 import**. framework 의존 0.
2. **`cases`는 라이브러리의 첫 번째 consumer + integration test 베드**. 539개 테스트가 사실상 패키지 검증.
3. **`runner.py`와 Streamlit은 같은 `scenario.run()`을 호출**. UI shell만 다름. 두 launcher 회귀 0.
4. **Backend DI 주입 지점**:
   - `runner.py`: 진입 시 `default_backends()` / `safe_backends()` (DEMO_SAFE 기준)
   - Streamlit: 사이드바 토글 또는 `.env`로 결정
   - **외부 컨설팅 프로젝트**: 자체 backend 주입 가능 — dogfood `FakeBackend` 주입 smoke가 매 PR 동작 검증

## 4. 데이터 흐름 + 동시성 처방 + 보안

### 4.1 데이터 흐름 (단일 user, 단일 process) + minimum 보안 (R1-C2 / R2-C1)

```
[User] ─upload─▶ [Streamlit (127.0.0.1:8501 default — 사내 IP 노출 차단)]
                     │
                     │ run_id = secrets.token_urlsafe(16)
                     │ runs/{run_id}/input/ 디렉토리 생성
                     │ - per-file 50MB cap, total 200MB cap
                     │ - extension allowlist (xlsx/csv/pdf/docx/hwpx/png/jpg)
                     │ - Path.resolve() ⊂ runs_root.resolve() (path traversal 방어)
                     ▼
                [scenario.run(
                    input_dir=runs/{id}/input,
                    output_dir=runs/{id}/output,
                    backends=resolved_backends(safe=sidebar_toggle),
                    progress_cb=streamlit_progress_adapter,
                    config={column_map, threshold, ...}
                 )]
                     │
                     │ progress_cb → ProgressEvent emit (R2-H3)
                     │ Streamlit adapter / FastAPI Redis adapter 양쪽 호환
                     ▼
                [ScenarioResult] → serialize_result() → run.json
                  ├─ summary_text   → st.success 카드
                  ├─ output_files[] → st.download_button per file
                  ├─ metrics{}      → st.dataframe (처리시간 / 성공·실패 카운트)
                  ├─ failures[]     → st.warning 표 (sanitizer 거친 후)
                  └─ extras{}       → case별 자유 영역 (case07 ReceiptData 100건 등)

runs/{run_id}/  (디렉토리 정책)
  ├─ input/
  ├─ output/
  └─ run.json  (serialize_result() 결과 — secrets_mask 자동 적용)

TTL cleanup 정책 (R2-C1 처방):
  (a) Streamlit start hook: mtime > 24h 디렉토리 sweep
  (b) scenario.run() 진입 시: lazy cleanup (mtime > 24h만)
  (c) runs/.gitignore: '*' + '!.gitkeep' (git 누출 차단)
  Phase 4 후보: cron actor / TTL 자동화
```

### 4.2 G1~G5 처방 — 책임 분리 명시 (R2-C2)

v1 design §2.2의 5개 깨지는 CLI 가정 중 단일 user에서도 처방이 필요한 것:

| # | 가정 | 단일 user 영향 | 처방 | 책임 분담 |
|---|---|---|---|---|
| G1 | `DEMO_SAFE` env = process-wide 토글 | 낮음 (단일 thread) | `contextvars.ContextVar` + `force_safe`도 ContextVar set (R1-H3) | `safe_mode_v2`: **safe 토글 상태**만 관리 |
| G2 | `safe_mode.intercept` = `unittest.mock.patch` (process global) | 중간 (Streamlit rerun이 import 재실행) | Backends DI로 이주 | **Backends**: 외부 호출 인터셉트·격리 |
| G3 | mlx_vlm.server 단일 인스턴스 직렬 | 없음 (자연 직렬) | 처방 불요 | — |
| G4 | output dir cwd 기준 | 중간 (CLI + Streamlit 동시 실행 충돌) | run_id 디렉토리 격리 + path traversal 방어 (R1-C2) | `web/app.py` + scenario `output_dir` 인자 |
| G5 | scenario가 `os.environ` / `Path("cases")` / `Path("personas/sample_data/...")` 직접 참조 9건 | **높음** — 외부 프로젝트가 import 시 깨짐 | scenario.run() 시그니처 정식화 + cwd-coupling 제거 | T32에서 별도 분해 (R3-C2) |

**책임 분리 lock**: `safe_mode_v2`는 "현재 safe 토글 상태"만 관리. **Backends DI**가 외부 호출 인터셉트·격리·캐시·force_safe 폴백을 모두 담당. 두 시스템이 같은 일을 중복하지 않음.

### 4.3 에러 처리 정책

1. **Backend 실패** → 폴백 체인 (`OpenRouter` 모델 폴백 → `force_safe()` ContextVar set)
2. **scenario 내부 실패** (한 건 OCR 실패 등) → `ScenarioResult.failures[]` 구조화. raise는 catastrophic만.
3. **Streamlit 측 catastrophic** → `st.error()` + traceback을 `serialize_result()` 거친 후 run.json 직렬화
4. **CLI(`runner.py`)도 동일 정책** — 두 launcher 일관성

## 5. 검증 전략 (다층 잠금 — 3.11 풀 + cross-version smoke)

### 5.1 Dogfood fixture project (R3-H1: FakeBackend 주입 검증 추가)

`tests/dogfood/` 안에 minimal `pyproject.toml` + smoke 스크립트:

```
[CI fresh venv, secret env 차단]
  assert not any(os.environ.get(k) for k in SECRET_ENV_NAMES)

[uv pip install --frozen ./packages/flowcoder-office-tools[ocr,messaging,docgen,ai]]
  → uv.lock 기반 supply chain pin (R1-H2)

[python -m dogfood_smoke]
  1. 모든 public API import (`from flowcoder_office_tools.excel import read_excel`, ...)
  2. SafeBackend 주입 → scenario.run() 1회 → 외부 호출 0건 통과
  3. **FakeBackend 주입** → scenario.run() 1회 → fake가 실제 호출되었는지 assert (R3-H1)
  4. ScenarioResult 형태 검증 (TypedDict 필드 5+1종 모두 존재)
  5. serialize_result() 거친 출력에 sentinel secret 없음 (R1-C1)
```

**dogfood limitation 명시 (R2-H2)**: dogfood는 **path install**만 검증. 외부 프로젝트의 git+ssh subdirectory dep install은 metadata/wheel build 경로 차이로 동작이 다를 수 있음. 게이트 (2)는 path install 보장만 — git+ssh 호환성은 게이트 (1) 외부 사용 시점에 자연 catch.

### 5.2 `__all__` lock + breaking change detector (R1-C3, R2-M2)

각 public 모듈에 `__all__` 명시:

```python
# flowcoder_office_tools/excel/__init__.py
__all__ = ["read_excel", "merge_files", "build_pivot", "write_workbook", "validate_columns"]
```

`tests/test_public_api_surface.py`:
- snapshot 대상 = **`__all__`에 명시된 심볼만** (모듈 내 internal symbol은 검사 제외)
- baseline 생성 시 **`_`-prefix 심볼 자동 제외** (R1-C3)
- `__all__` 미명시 모듈은 dogfood smoke가 fail
- snapshot 변경 시 → 테스트 실패 → PR description에 **BREAKING CHANGE: ...** 강제 (수동 confirm 후 snapshot 갱신 commit)

### 5.3 Cross-version (Python 3.11 풀 + 3.12 / 3.13 smoke; R3-C3)

GitHub Actions matrix:
- **3.11**: full pytest (539+4 + 신규 80+) + mypy --strict + ruff
- **3.12 / 3.13**: dogfood smoke + `__all__` import만 (외부 lib 호환성만 catch)

**framing 정직**: 본 design은 **3.11 풀 잠금** + **3.12/3.13 cross-version smoke**. 3.12/3.13에서 539개 회귀 테스트가 매번 도는 것은 아님.

CI cost (R3-M1 누락 risk 흡수): 3 jobs × pytest 539 = ~3x runtime이 아니라 (3.11만 539 + 3.12/3.13은 smoke 수십 개) 약 1.3x. 매 PR 5~7분.

### 5.4 회귀 0 + 신규 테스트 (minimum 카운트, R3-M2)

| 항목 | T28 baseline (cf76f50) | Phase 3 종료 minimum |
|---|---|---|
| pytest | 539 passed + 4 skipped | **620+** (Backends DI ≥30, contextvars safe_mode_v2 ≥10, scenario sigchg 회귀 보강 ≥20, dogfood ≥10, public API surface ≥5, Streamlit smoke ≥5) |
| mypy --strict source files | 53 | **70+** (`packages/flowcoder-office-tools/src/`, `web/app.py` 추가) |
| ruff check / format --check | clean | clean |
| 시연 가능 case | 10/10 (CLI) | 10/10 (CLI + Streamlit) |
| e2e smoke | runner.py 4건 | runner + Streamlit 4건 |

**minimum 미충족 시 정책**: T34 통합 검증 시점에 항목별 카운트 부족 → 추가 작성 (T34 추정 +0.5d 흡수). 라벨링/round 인정은 금지.

### 5.5 검증 게이트 매핑

| 검증 항목 | local | CI | 실패 시 |
|---|---|---|---|
| pytest 539+4 회귀 0 | 매 commit | 매 push | merge block |
| 신규 backends/contextvars/scenario tests | 매 commit | 매 push | merge block |
| dogfood smoke (fresh venv, FakeBackend, secret env 차단) | optional | 매 PR | merge block |
| `__all__` surface snapshot (`_`-prefix 제외) | 매 commit | 매 push | snapshot 변경 시 PR description gate |
| cross-version (3.12 / 3.13) smoke | optional | 매 PR | merge block |
| ruff check + format --check | 매 commit | 매 push | merge block |
| mypy --strict (cumulative lock) | 매 commit | 매 push | merge block |
| 3-reviewer audit (R1 보안 / R2 아키 / R3 정직성) | — | Phase 3 종료 시 (T46) | critical 0건 / high는 fixer commit |

**핵심 약속 (정정)**: 이 다층 잠금 통과 + 외부 사용 1회 이상 시연 + 피드백 수집한 패키지는 **다른 프로젝트의 빈 venv에 `pip install`하면 그대로 동작**. dogfood + FakeBackend smoke가 매 PR마다 자동 증명, 외부 사용 row는 reviewer feedback의 실증.

## 6. Task Map + 추정 (정직 정정) + Risks

### 6.1 Task Map

```
T31 docs(design v2.1)        ── audit findings 반영 (이 commit)
T32 docs(retract)            ── 외부 사용 0/2 미충족 정직 인정 + production-ready 라벨 retract
T33 docs(gate)               ── v2.1 게이트 정의 정합화 (4 파일)
   ↓
3-A Refactor (T34~T40)       ──┐
                                │ 즉시 wins (W1~W3) 병렬 진행
3-Pkg Extraction (T41~T45)   ──┤
                                │
3-Web Streamlit MVP (T46~T49)──┘
   ↓
Phase 3 close (T50~T51)
```

### 6.2 Task 분해 (R3-C2 정직 정정 — T32/T36 분해, 합계 ~13d)

| ID | 작업 | 산출물 | 추정 |
|---|---|---|---|
| **T31** | docs — design v2.1 audit findings 반영 (이 commit) | design-v2.md 갱신 | ~45분 |
| **T32** | docs — retract-only commit (외부 사용 0/2 미충족 인정 + production-ready 라벨 retract) | 명시적 retract row | ~20분 |
| **T33** | docs — v2.1 게이트 정의 정합화 (promise.md + README + CLAUDE + MEMORY 4 파일 cross-link) | 4 파일 갱신 | ~25분 |
| **T34** | `cases/_protocols.py` — ScenarioResult TypedDict (+`extras`) + `serialize_result()` + Backends frozen dataclass + Backend Protocol (audit log contract) + 30+ tests (sanitizer + sentinel secret) | 신규 1 file (mypy 53→54) + tests | 0.75d |
| **T35** | `core/backends/` — MLX/OpenRouter/Discord/Gmail/Safe/Cached 구현 + cache key sha256 + backend fingerprint + 30+ tests | 신규 1 dir + tests | 1d |
| **T36** | `core/common/safe_mode_v2.py` — contextvars 기반 + `force_safe`도 ContextVar set + 기존 safe_mode shim | 신규 1 file + tests | 0.5d |
| **T37** | case01~case10 scenario 시그니처 정식화 (keyword-only) + runner.py 디폴트 채움 | 10 scenarios + runner | 1d |
| **T38** | G5 cwd-coupling 제거 — scenario 9건 `Path("personas/...")` / `Path("cases/...")` 직접 참조 모두 input_dir/output_dir 인자로 | 10 scenarios cleanup | 0.75d |
| **T39** | progress_cb 표준화 — `Callable[[ProgressEvent], None]` 시그니처 (Streamlit/FastAPI 양호환, R2-H3) + CLI rich.progress 어댑터 | runner 헬퍼 + cases 루프 | 0.75d |
| **T40** | Phase 3-A 통합 검증 (mypy/pytest/ruff full) + 카운트 minimum 검증 | 회귀 0 증빙 | 0.5d |
| **T41** | `packages/flowcoder-office-tools/` scaffold — uv workspace pyproject + showcase pyproject 갱신 | 신규 dir + 양쪽 pyproject | 0.5d |
| **T42** | `core/` → `packages/.../src/flowcoder_office_tools/` 이주 (libcst codemod) — import path migration | 60+ files move + import 갱신 | 1d |
| **T43** | shim 안정화 — 양쪽 import 공존 검증 + 회귀 0 | shim 모듈 | 0.5d |
| **T44** | `__all__` 명시 (`_`-prefix 자동 제외) + `tests/test_public_api_surface.py` + signature snapshot baseline (shim 제거 후 작성) | 신규 1 test + snapshot json | 0.5d |
| **T45** | shim 제거 + `tests/dogfood/` fixture (FakeBackend + secret env 차단 + uv.lock frozen) + CI matrix (3.11/3.12/3.13) | shim 제거 + dogfood + workflow | 1d |
| **T46** | `web/app.py` 골격 — 10 case 카드 메뉴 + 127.0.0.1 default + size cap | 신규 1 file | 0.75d |
| **T47** | 입력 업로드 + run_id 디렉토리 격리 + path traversal 방어 + scenario.run() 직접 호출 | web/app.py 확장 | 1d |
| **T48** | progress_cb adapter + 결과 카드 (download/summary/metrics/failures/extras 표) + TTL cleanup hook | web/app.py 마무리 | 0.5d |
| **T49** | Phase 3-Web 통합 검증 + Streamlit smoke test | 신규 e2e test | 0.5d |
| **T50** | 3-reviewer audit (R1 보안 / R2 아키 / R3 정직성) | findings 정리 | 0.5d |
| **T51** | Phase 3 close — README/CLAUDE/MEMORY 갱신 + 외부 사용 추적표 update + Phase 4 backlog | docs commit | 0.5d |
| **W1** | E4B 4bit 다운로드 + symlink (병렬, 사용자 환경) | symlink 갱신 | 0.5d |
| **W2** | Few-shot prompting 강화 (`core.ocr.gemma._default_prompt`) | prompt 수정 + 100장 검증 | 0.5d |
| **W3** | `runner.py --warmup-blocking` | runner 옵션 추가 | 0.25d |

**추정 합계** (R3-C2 정정): T34~T40 합 5.25d + T41~T45 합 3.5d + T46~T49 합 2.75d + T50~T51 합 1d = **~12.5d** (W는 3-A와 병렬 → 실 wallclock ~12d). T31~T33 docs는 별도 ~1.5h.

### 6.3 Risks

| # | Risk | 처방 |
|---|---|---|
| R1 | 패키지 분리 시 import path 변경으로 모든 case 깨짐 | T42 libcst codemod로 자동화. T43에서 shim 안정화. T44 snapshot은 **shim 제거 후** baseline (R3-H3) |
| R2 | dogfood fixture가 mlx_vlm.server 외부 의존 | dogfood smoke는 SafeBackend + FakeBackend만 사용 — 외부 호출 0건 통과 |
| R3 | `__all__` snapshot이 너무 엄격 → 일반 리팩터도 PR block | snapshot 대상 = `__all__` 명시 심볼만. 모듈 내 internal/`_`-prefix 자동 제외 |
| R4 | Streamlit rerun 모델이 import-time mutation에 취약 | Backends DI로 모든 외부 의존 함수 인자화. `force_safe`도 ContextVar set (`os.environ` mutation 0) |
| R5 | 외부 사용 게이트 미충족 (1) + 마감 2026-05-09 | T32 retract-only commit으로 솔직 인정. dogfood (2)는 추가 검증이지 (1)의 대체 아님 (R3-C1) |
| R6 | `safe_mode_v2` ↔ Backends DI 책임 중복 | §4.2에 책임 분리 lock — `safe_mode_v2`는 토글 상태만, Backends가 외부 호출 격리 (R2-C2) |
| R7 | Streamlit `session_state` ↔ stateless 충돌 | UI state는 Streamlit, 비즈니스 state는 `run.json` (디스크). scenario.run()은 stateless 유지. progress_cb는 fire-and-forget event (R2-H3) |
| R8 | dogfood path install vs 외부 git+ssh install 차이 | §5.1 limitation 명시. git+ssh 호환성은 외부 사용 게이트 (1) 시점에 자연 catch |
| R9 | 다음 컨설팅 프로젝트가 Python 3.10이거나 conda 환경 | **3.11/3.12/3.13 matrix가 catch 못 함**. README에 "지원 Python = 3.11~3.13" 명시. 3.10 요구 시 별도 호환성 작업 |
| R10 | Linux runner에서 macOS-only 의존성 (mlx_vlm 등) import-time mutation | dogfood smoke는 macOS 외 환경에서 SafeBackend만 사용 — `[ocr]` extras를 install하지 않는 minimum 모드 fallback |
| R11 | Streamlit multi-tab single user 시 cross-run state 누수 | `st.session_state`를 run_id 키로 namespace. tab간 격리. T46/T47 |
| R12 | sanitizer가 false negative — 새 secret 패턴 미반영 | T34 sentinel secret test가 OAuth/Bearer/SSH key 등 cover. 신규 패턴 발견 시 `secrets_mask` 추가 + 테스트 추가 |

## 7. 결정 미루기 (Phase 4 후보)

- 자체 모델 fine-tune (영수증 카테고리 분류기, 한국어 OCR 정확도 향상)
- 사내 vector DB + RAG (회의록/제안서 사내 룰 자동 적용)
- whisper 통합 (case10 deferred decision matrix per `specs/case10-whisper-decision.md`)
- HWPX 실시간 미리보기 재평가 (rhwp 후속 또는 LibreOffice headless)
- 모바일 (사진 업로드 → 영수증 OCR) — 사내 영업 직원용
- TTL 자동화 (cron actor / systemd timer)
- **외부 N user 결정 시점에 추가**: FastAPI 라우트, Dramatiq 큐, MinIO/S3, Postgres, Auth.js — v1 design 문서의 §5~§7 그대로 reference. swap 비용 합 ~1주 (§0.1 표 disclose).

## 8. 외부 사용 시나리오 (v2.1 정정)

§2.2 게이트 두 트랙:

### 8.1 외부 사용 약속 (1) — 외부 reviewer feedback 본래 우려

- **Phase 2 약속 보존** — 실 미팅·강의 1회 이상 시연 + `specs/phase2-external-usage-promise.md` 추적표 row append
- 시연 케이스 자유 (case01/02/03/04/05/07/09/10 중)
- **마감 2026-05-09** — 미충족 시 T32 retract commit (production-ready 라벨 retract + 외부 reviewer feedback 미수집 인정). 이는 게이트 (2) dogfood로 대체되지 않음.

### 8.2 dogfood fixture (2) — 추가 검증 (코드로 재사용 가능성 증명)

- T45 시점에 활성화. CI에서 fresh venv → `pip install` → smoke (FakeBackend 주입 + secret env 차단) 통과.
- T45 종료 후 영구 PR merge 차단 조건. 회귀 시 즉시 catch.
- (1)을 **대체하지 않음** — 자기 코드가 자기 코드를 import할 뿐, 외부 reviewer feedback 부재 우려는 (1)이 담당.

### 8.3 라벨 분리 (R3-L3)

- 게이트 (1) + (2) 동시 충족 → "**검증된 재사용 라이브러리** + 외부 시연 검증"
- 게이트 (2)만 → "**import-ready 패키지** (재사용 가능성 코드로 증명, 외부 reviewer feedback 미수집)"
- 둘 다 미충족 → "Phase 3 코드 진입 차단"

## 부록 A. 10-case 출력 매트릭스 (R2-C3)

ScenarioResult 5+1 필드가 10 case 출력을 흡수 가능한지 dry run:

| Case | summary_text | output_files | metrics | failures | extras |
|---|---|---|---|---|---|
| case01 | "거래처 12개월 매출 보고서 생성" | `vendor_monthly_report.xlsx` | `{rows: 720, vendors: 60, sheets: 1}` | (없음) | — |
| case02 | "단가 검증 + Discord 이상치 N건 알림" | `unit_price_outliers.xlsx` | `{outliers: 8, total: 200, discord_sent: 8}` | (없음 또는 webhook 실패) | `outlier_z_scores: list` |
| case03 | "견적 메일 50건 발송 (PDF 첨부)" | `quotes/*.pdf` (50개) | `{sent: 48, pdf_failed: 2}` | `[{vendor, error}, ...]` (2건) | — |
| case04 | "미수금 60건 단계별 Discord 알림" | (없음) | `{stage_a: 24, b: 18, c: 12, d: 6, sent: 60}` | (webhook 429 등) | — |
| case05 | "견적서 10건 Word + PDF 생성" | `quote_*.docx`, `quote_*.pdf` (20개) | `{requests: 10, docx: 10, pdf: 10}` | (md_to_pdf 실패) | — |
| case06 | "정부지원사업 신청서 HWPX 생성" | `application_form.hwpx` | `{cells_filled: N}` | (HWPX 양식 필드 누락) | — |
| case07 | "영수증 100장 OCR + 경비 엑셀" | `expenses.xlsx` | `{ocr_total: 100, success: 88, failed: 12, avg_seconds: 2.1}` | `[{img, error, retry_count}, ...]` (12건) | `receipts: list[ReceiptData]` (100건) |
| case08 | "세금계산서 30장 OCR + 회계 CSV" | `accounting.csv` | `{ocr_total: 30, success: 28, failed: 2, biznum_validated: 28}` | `[{img, error}, ...]` (2건) | `invoices: list[InvoiceData]` (30건) |
| case09 | "거래처 응대 메일 AI 초안 (3안)" | `drafts/*.txt` (3개) | `{drafts: 3, model: gemini-2.5-flash, tokens: 1200}` | (model fallback 발생) | `drafts: list[str]` (요약 노출) |
| case10 | "회의록 5건 요약 + 액션아이템" | `meeting_summaries.xlsx` | `{meetings: 5, action_items: 23, owners_assigned: 18}` | (owner hallucinate 검출) | `summaries: list[MeetingSummary]` |

**검증**: 모든 case가 5+1 필드로 흡수 가능. `extras`는 case별 자유 영역 (case07 ReceiptData 100건처럼 큰 dict는 metrics 대신 extras로). dogfood smoke는 5필드만 검증, extras는 case별 별도 테스트.

## 9. Glossary

- **dogfood fixture** — 다른 프로젝트가 패키지를 import하는 환경을 재현하는 CI 단계. FakeBackend 주입 검증 포함.
- **DI** — Dependency Injection. 현 monkey patch 대체.
- **fire-and-forget event** — progress_cb 시그니처 `Callable[[ProgressEvent], None]`. Streamlit / FastAPI Redis 양 어댑터 호환.
- **G1~G5** — v1 design §2.2의 5개 깨지는 CLI 가정. v2.1 §4.2에서 단일 user에 살아있는 것 + 책임 분리 lock.
- **monorepo workspace dep** — uv workspace `tool.uv.workspace.members = ["packages/flowcoder-office-tools"]` + showcase pyproject가 path dep로 참조.
- **public API surface** — `__all__`로 노출된 심볼 + signature. `_`-prefix 자동 제외.
- **ScenarioResult** — 모든 case scenario.run()의 표준 반환 TypedDict. 5필드 + `extras`.
- **serialize_result()** — ScenarioResult를 디스크/JSON으로 직렬화하는 단일 진입점. `secrets_mask` 자동 적용.
- **shim 단계** — `core/`와 `packages/.../flowcoder_office_tools/` 두 import path 공존. T43 안정화 → T45 제거.
- **Streamlit MVP** — FastAPI 없이 Streamlit이 직접 cases.scenario.run()을 호출하는 단일 process 사내 시연 도구. 127.0.0.1 default + minimum 보안.
- **W1~W3** — 즉시 wins. E4B 4bit / few-shot / warmup-blocking. 3-A와 병렬 가능.

## 10. 변경 이력

- **2026-05-08 v1**: Phase 3 design 초안 (5 sub-phase, SaaS 방향까지 커버). HEAD `4537919`. 작성자: Claude Opus 4.7.
- **2026-05-08 v2**: 사용자 의도 재정렬 (재사용 우선 + 사내 단일 user 데모). FastAPI/Queue/DB/Multi-tenant 컷, 패키지화 1순위 승격, 풀 잠금 검증 추가. HEAD `acb8cb8`.
- **2026-05-08 v2.1** (이 갱신): 3-reviewer audit (R1 보안 / R2 아키 / R3 정직성) findings 17건 반영. 핵심 정정:
  - R3-C1 게이트 회피 정정 — 외부 사용 약속 (1) 보존, dogfood (2)는 추가 검증
  - R3-C2 추정 정직 — T32/T36 분해, 합계 ~10.5d → ~12.5d
  - R3-C3 framing 정정 — "풀 잠금" → "다층 잠금 (3.11 풀 + cross-version smoke)"
  - R1-C1/C2/C3 — sanitizer / Streamlit 보안 / underscore 제외 명시
  - R2-C1/C2/C3 — TTL cleanup / safe_mode_v2 ↔ Backends 책임 분리 / ScenarioResult universality (부록 A)
  - R1/R2/R3 high+ findings 11건 — 본문 §3~§6에 흡수
