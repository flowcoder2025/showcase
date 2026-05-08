# AX Showcase — Phase 3 Design (Web 모듈화 + 코어 패키지화)

작성: 2026-05-08
대상 HEAD: `cf76f50` (T28 — Ollama → MLX 백엔드 전환 완료)
관련: `specs/2026-04-30-design.md` v2.1, `specs/2026-05-01-phase2-plan.md`

## 0. Scope / Non-goals

### Scope
- 현재 CLI 전용 시연 자산을 **두 번째 컨설팅 프로젝트에서 import-friendly한 코어 라이브러리** + **웹 데모/내부 도구로 동시에 활용 가능한 Layered 구조**로 발전시킨다.
- 시연 임팩트를 유지(또는 강화)하면서, 동시 요청·진행률·결과 영속·DI·관측성 등 웹 환경 필수 요소를 정합적으로 추가한다.
- `core/`을 별도 패키지(`flowcoder-office-tools`)로 분리해 PyPI private 또는 git+ssh 의존으로 import 가능하게 한다.

### Non-goals (이번 Phase 3에서 의도적으로 제외)
- 외부 SaaS 출시 / 결제 / 멀티 테넌시 정식 운영 — 사내 도구·시연 데모 범위 우선.
- 실시간 음성 → 텍스트 (case10 whisper deferral은 별개 trace, `specs/case10-whisper-decision.md` 참조).
- ML 모델 자체의 fine-tune / 자체 hosting 자동화 — `mlx_vlm.server` 외부 reference 그대로 사용.
- HWPX 실시간 미리보기 (rhwp PoC 5옵션 모두 실패 후 deferred — `specs/rhwp-poc-decision.md`).

## 1. 외부 사용 게이트와의 관계 (Honesty)

`specs/phase2-external-usage-promise.md`에 명시된 약속:

> Phase 2 종료 후 실 미팅 또는 강의에서 **2회 이상** 사용 → 피드백 반영 후 Phase 3 진입.
> 하드 마감: 2026-05-09. 미충족 시 production-ready 주장 retract + Phase 3 게이트 차단.

2026-05-08 시점 충족: **0/2**.

본 design + plan 문서 작성·commit은 **코드 변경이 없는 설계 작업**으로, 게이트의 정신("피드백 반영")과 충돌하지 않는다. 단:

- **코드 진입 (Phase 3-A 이후)은 게이트 충족 또는 명시적 retract 후에만 시작.**
- 게이트 미충족인 채로 Phase 3 코드 작업이 시작될 경우, 본 design 문서 §11(Risks)에 retract 사유와 일자를 추가하고 README/CLAUDE/MEMORY의 production-ready 주장을 동시 retract한다.
- 본 문서가 정식 design이 됨으로써, 다음 세션에서 진입 결정만 받으면 즉시 task 단위 작업이 가능해진다.

## 2. 현 구조 평가

### 2.1 강점 (그대로 보존)
- **Layered 분리**: `core/`(CLI 무관) ⊥ `cases/`(thin scenario wrapper) ⊥ `runner.py`(launcher). 이미 두 번째 프로젝트 import 사용에 가까운 형태.
- **safe_mode 단일 경계**: `runner.py`가 sole intercept boundary. case는 자체 wrap 금지.
- **모듈 참조 호출 컨벤션**: `from core.ai import client; client.chat()`. 외부 호출 가로채기(monkey patch) 단일 진입점 보장.
- **OpenRouter 폴백 체인 + force_safe 자동 폴백**: 외부 API 실패가 시연 흐름을 깨뜨리지 않는다.
- **MLX subprocess manager (T28)**: 좀비 0 + 메모리 회수 보장.

### 2.2 깨지는 5개 CLI 가정 (Web 환경에서)

| # | CLI 가정 | Web 환경에서 깨짐 | 우선순위 |
|---|---|---|---|
| **G1** | `DEMO_SAFE` env var = process-wide 토글 | 한 워커가 여러 요청 처리 시 request마다 모드가 다를 수 있다 → race | 높음 |
| **G2** | `safe_mode.intercept` = `unittest.mock.patch` (process global) | 동시 요청 race — patch가 다른 요청에 새어 들어간다 | 높음 |
| **G3** | mlx_vlm.server 1 요청/시점 직렬 처리 | 동시 OCR 10개 → 9개 대기, timeout/SLA 위반 | 중간 |
| **G4** | 결과 파일 = `cases/<id>/output/<file>` (cwd 기준) | 사용자별 격리·다운로드·만료·동시 실행 충돌 | 중간 |
| **G5** | scenario가 `os.environ` / `Path("cases")` / `Path("personas/sample_data/...")` 직접 참조 | 웹 worker는 cwd 가정 못 함, 입력은 업로드된 임시 디렉토리 | 높음 |

각 가정의 처방은 §4~§6에 매핑된다.

## 3. Target 아키텍처

```
            ┌─────────────────────────────────────────┐
            │  Frontend (Next.js or Streamlit MVP)    │  ← Phase 3-D / 3-B
            └────────────────┬────────────────────────┘
                             │ HTTPS (multipart upload + JSON + SSE)
            ┌────────────────▼────────────────────────┐
            │  FastAPI (Phase 3-B+)                   │
            │  - POST /runs (case_id + files)         │
            │  - GET  /runs/{id}        (status)      │
            │  - GET  /runs/{id}/events (SSE 진행률)   │
            │  - GET  /runs/{id}/output/{name}        │
            │  - 인증 미들웨어 (Phase 3-E)             │
            └────────────────┬────────────────────────┘
                             │ enqueue(run_id, case_id, input_uri)
            ┌────────────────▼────────────────────────┐
            │  Job Queue (Dramatiq + Redis)           │  ← Phase 3-C
            └────────────────┬────────────────────────┘
                             │ run scenario(input_dir, output_dir, backend, progress_cb)
            ┌────────────────▼────────────────────────┐
            │  Worker process(es)                     │
            │  - import flowcoder_office_tools.*      │
            │  - import cases.<id>.scenario           │
            │  - Backend DI: Real / Cached / Safe     │  ← Phase 3-A
            │  - progress_cb → Redis pub/sub          │
            └────────────────┬────────────────────────┘
                             │ vision API / chat API / SMTP / webhook
            ┌────────────────▼────────────────────────┐
            │  Backends (외부)                         │
            │  - mlx_vlm.server pool (E2B/E4B)        │  ← T28 그대로
            │  - OpenRouter (AI)                      │
            │  - Discord webhook                      │
            │  - Gmail OAuth / SMTP                   │
            └─────────────────────────────────────────┘

            ┌─────────────────────────────────────────┐
            │  Object Storage (MinIO 사내 / S3 외부)  │  ← Phase 3-C
            │  - inputs/{run_id}/<file>               │
            │  - outputs/{run_id}/<file>              │
            │  TTL 24h (시연용), 7d (사내용)            │
            └─────────────────────────────────────────┘

            ┌─────────────────────────────────────────┐
            │  Postgres (사내 / Supabase 외부)        │  ← Phase 3-C
            │  - runs (id, case_id, status, created)  │
            │  - run_events (run_id, ts, payload)     │
            └─────────────────────────────────────────┘
```

### 3.1 Layer 책임

| Layer | 책임 | 의존 방향 |
|---|---|---|
| `flowcoder_office_tools/*` (현 `core/`) | 비즈니스 로직 (excel/messaging/docgen/ocr/ai). 외부 IO는 protocol 인터페이스로만 노출. | 무 (stdlib + pinned deps) |
| `cases/<id>/scenario.py` | 입력 → 코어 호출 → 출력 파일 생성 + ScenarioResult 반환. **stateless 함수만**. | core lib |
| `runner.py` | CLI launcher. 인자 파싱, 메뉴, MLX subprocess spawn, scenario 호출. | core + cases |
| `web/api.py` (신규) | FastAPI 라우트. 업로드 수신, run_id 발급, queue enqueue, SSE 스트리밍. | core + cases (간접: queue 통해) |
| `web/worker.py` (신규) | Dramatiq actor. queue 메시지 수신 → scenario.run() 호출 → progress 발행 → 결과 업로드. | core + cases |

CLI(`runner.py`)와 Web(`web/api.py + web/worker.py`)은 **모두 같은 scenario 함수를 호출**한다. case 로직은 단일 truth source.

## 4. 모듈화 리팩터 (Phase 3-A) — 코드 영향 작은 기반 작업

이 단계만 끝나면 외부 컨설팅 프로젝트에서 `import flowcoder_office_tools` 가능 + 웹 layer가 깨끗하게 위에 얹힌다. **CLI는 회귀 0**.

### 4.1 ScenarioResult TypedDict — `cases/_protocols.py` (신규)

```python
class ScenarioResult(TypedDict):
    """모든 case scenario.run()의 표준 반환 타입."""
    case_id: str
    summary_text: str            # CLI 출력 + Web summary 카드용
    output_files: list[Path]     # 절대경로 (or output_dir 상대경로)
    metrics: dict[str, Any]      # 처리시간, 성공/실패 카운트 등
    failures: list[dict[str, Any]]  # case07 OCR 실패 12건 같은 구조화 실패
```

기존 `cases/<id>/scenario.py::run()`이 `int` 반환 + 부수효과로 파일 생성하던 패턴을 깨고, **`ScenarioResult`로 일원화**. CLI(`runner.py`)는 result.output_files를 finder로 열고, Web(`worker.py`)은 object storage에 업로드.

### 4.2 scenario.run() 시그니처 정식화

현재 (case별 상이):
```python
def run() -> int:
    in_dir = Path("personas/sample_data/receipts")
    out_dir = Path(__file__).parent / "output"
    ...
```

후:
```python
def run(
    *,
    input_dir: Path,
    output_dir: Path,
    backend: Backends | None = None,                  # DI (None → default real)
    progress_cb: Callable[[int, int, str], None] | None = None,  # processed, total, label
    config: dict[str, Any] | None = None,             # case별 dial (column_map, threshold 등)
) -> ScenarioResult:
    ...
```

`runner.py`가 default `input_dir` / `output_dir`을 메뉴 모드에서 그대로 채워줌 → CLI 호출 회귀 0. 웹은 업로드된 임시 디렉토리 + 객체 스토리지 prefix로 채움.

### 4.3 Backend protocol (`core/backends.py` 신규)

```python
class OCRBackend(Protocol):
    def extract(self, image_path: Path, *, model: ModelLiteral, schema: dict | None) -> dict: ...

class AIBackend(Protocol):
    def chat(self, messages: list[dict], *, model: str | None = None) -> str: ...

class MessagingBackend(Protocol):
    def send_discord(self, content: str, *, level: str) -> None: ...
    def send_email(self, message: EmailMessage) -> None: ...

@dataclass(frozen=True)
class Backends:
    ocr: OCRBackend
    ai: AIBackend
    msg: MessagingBackend
```

기본 구현:
- `MLXBackend` — 현 `core.ocr.gemma.extract` 위임
- `OpenRouterBackend` — 현 `core.ai.client.chat` 위임
- `DiscordWebhookBackend`, `GmailBackend` — 현 messaging 모듈 위임
- `SafeBackend(*) ` — `force_safe` 시 deterministic dummy. monkey patch 의존 제거 (G2 처방).
- `CachedBackend(real, store)` — 캐시 hit → 위임 wraps real.

웹 worker는 request 시점에 `Backends(...)` 조립해 scenario에 주입. 동시 요청이 각자 다른 backend(real / safe)를 사용해도 격리 (G1·G2 처방).

### 4.4 contextvars safe mode (`core/safe_mode_v2.py` 신규)

`os.environ["DEMO_SAFE"]` → `contextvars.ContextVar[bool]` 전환:

```python
_SAFE_VAR: ContextVar[bool] = ContextVar("safe_mode", default=False)

def is_safe() -> bool:
    return _SAFE_VAR.get()

@contextmanager
def safe_mode_scope(enabled: bool = True) -> Iterator[None]:
    token = _SAFE_VAR.set(enabled)
    try:
        yield
    finally:
        _SAFE_VAR.reset(token)
```

호환성: 기존 `os.getenv("DEMO_SAFE")` 호출은 contextvars의 default를 env에서 1회 초기화. CLI는 진입 시 한 번만 ContextVar 세팅 → 회귀 0. 웹은 request마다 scope wrapping → 격리 (G1 처방).

기존 `safe_mode.intercept(case_id, apis=[...])` (monkey patch)는 deprecate하고 Backends DI로 이주 (G2 처방). 단계적 — Phase 3-A 끝까지 둘 공존, 3-B 진입 시 mp 제거.

### 4.5 progress_cb 표준화

각 case 시나리오의 루프(예: case07의 100장 OCR)에서:
```python
for i, img in enumerate(images, 1):
    result = backend.ocr.extract(img, model="gemma4:e2b", schema=RECEIPT_SCHEMA)
    if progress_cb:
        progress_cb(i, len(images), f"{img.name}")
    ...
```

웹 worker는 `progress_cb`를 Redis pub/sub publish로 구현 → FastAPI SSE가 subscribe → 프론트 진행바.
CLI는 `rich.progress.Progress` 인스턴스를 callback으로 wrap.

## 5. Web Layer (Phase 3-B) — FastAPI prototype

### 5.1 라우트 (case07 우선)

| Method | Path | 설명 |
|---|---|---|
| `POST` | `/v1/cases` | 사용 가능한 case 목록 (meta.yaml 파생) |
| `POST` | `/v1/runs` | multipart: case_id + files[]. 응답: `{run_id}`. 즉시 202 반환 후 background. |
| `GET` | `/v1/runs/{run_id}` | 상태 조회 — pending/running/done/failed + ScenarioResult 요약 |
| `GET` | `/v1/runs/{run_id}/events` | SSE 진행률 (`event: progress`, `data: {processed, total, label}`) |
| `GET` | `/v1/runs/{run_id}/output/{name}` | output 파일 다운로드 (presigned URL 또는 stream) |
| `DELETE` | `/v1/runs/{run_id}` | 결과 삭제 (object storage + DB row) |

3-B는 **단일 process 동기 실행** (큐 없음, FastAPI BackgroundTask). 3-C에서 큐 도입.

### 5.2 의존성

- `fastapi`, `uvicorn[standard]`, `python-multipart`, `httpx` (테스트), `aiofiles`
- 큐 (3-C): `dramatiq[redis]`, `redis`
- 스토리지 (3-C): `boto3` 또는 `minio` (MinIO 우선 — 로컬 시연 자기완결)
- DB (3-C): `sqlmodel` 또는 `psycopg[binary]` + Alembic

### 5.3 인증 (3-E)

3-B/3-C는 인증 없음 (사내 시연 전제). 3-E에서:
- 사내: 정적 API 키 (env) + IP allowlist
- 외부: Auth.js / Supabase / Clerk 중 택 1 (별도 DD)

## 6. Phase 3-C — Queue + Storage + DB

### 6.1 큐: Dramatiq + Redis

선택 근거:
- 단순한 메시지 큐 + 미들웨어 시스템 (재시도, 시간 제한)
- Celery 대비 가벼움, RQ 대비 견고
- Python 기반 (FastAPI worker와 같은 lib)

Actor 예시:
```python
@dramatiq.actor(time_limit=15 * 60_000, max_retries=2)
def run_scenario_actor(run_id: str, case_id: str, input_uri: str) -> None:
    ...
```

**OCR concurrency 제어** (G3 처방):
- mlx_vlm.server 단일 인스턴스 = 사실상 직렬. Dramatiq에 OCR 전용 큐 + worker 1개 (concurrency=1) → 자연스러운 직렬화.
- 다른 case (excel/messaging/docgen/ai)는 `default` 큐 + concurrency=4 정도.

### 6.2 결과 영속

input/output 파일 → MinIO/S3 prefix `runs/{run_id}/`. 메타 → Postgres `runs` 테이블.

```sql
CREATE TABLE runs (
  id UUID PRIMARY KEY,
  case_id TEXT NOT NULL,
  status TEXT NOT NULL,  -- pending|running|done|failed
  result JSONB,           -- ScenarioResult 직렬화
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  expires_at TIMESTAMPTZ  -- TTL 정리 잡
);
```

TTL 정리 — Dramatiq cron actor가 daily.

## 7. Phase 3-D — Frontend

### 7.1 단계 분할
- **3-D1 Streamlit MVP** (1~2일): 빠른 사내 시연용. 같은 FastAPI 위에 Streamlit이 client로 동작.
- **3-D2 Next.js 정식** (1주): 외부 시연 / 정식 배포 시. Next.js 15 + shadcn/ui (FlowCoder 디자인 시스템 연계).

3-D1만으로도 외부 미팅에 들고 갈 수 있는 데모. 3-D2는 정식 출시 시.

### 7.2 핵심 화면 (3-D1)

1. **Case 선택**: 10개 카드 (현 메뉴 그대로)
2. **입력 업로드**: drag&drop (영수증/세금계산서) 또는 텍스트 입력 (회의록) 또는 form (견적/메일)
3. **실행 + 진행률**: SSE 진행바 + 실시간 카운터
4. **결과**: 다운로드 버튼 + 미리보기 (xlsx → 첫 시트 HTML 렌더, csv → 표, docx → 변환된 PDF iframe)

## 8. 패키징 — `flowcoder-office-tools`

### 8.1 분리 전략

```
flowcoder-office-tools/        ← 신규 git repo
├── pyproject.toml
├── src/flowcoder_office_tools/
│   ├── excel/
│   ├── messaging/
│   ├── docgen/
│   ├── ocr/
│   ├── ai/
│   └── common/
└── tests/

showcase/                       ← 현 레포
├── pyproject.toml              ← flowcoder-office-tools git+ssh dep
├── cases/
└── runner.py
```

**언제**: Phase 3-A 끝(또는 두 번째 컨설팅 프로젝트가 `core/`을 import하기 직전).
**검증**: 현 showcase가 새 패키지로부터 import해 567+ tests 모두 통과 + mypy strict 통과.

### 8.2 마이그레이션 안전장치

- `core/`을 한 번에 옮기지 않고 **shim 단계**: showcase 안에서 `core` → `flowcoder_office_tools`로 별칭 import. 양쪽 둘 다 잠시 import 가능하게 두고, 모든 import 사이트 옮긴 후 shim 제거.
- 패키지 분리 commit은 별도 PR (코드 변경 0, import path만).

## 9. 비기능 요구

### 9.1 동시성
- OCR worker concurrency = 1 (mlx_vlm.server 단일 인스턴스 직렬). E2B/E4B 분리로 alias별 concurrency=1씩 (사실상 2 동시).
- 그 외 case는 worker concurrency 4 (CPU-bound가 아니라 IO-bound 위주).

### 9.2 캐시
- 현 `core.common.safe_mode.cache_path`는 case별 디렉토리. Web에선 Redis 또는 Postgres LRU로 이동.
- 캐시 키: case_id + input file SHA256 + scenario version. Phase 3-A에서 캐시 인터페이스 protocol화.

### 9.3 보안 / PII (외부 공개 시)
- 업로드 파일은 멀웨어 검사 (clamav 사이드카) — 사내 시연은 skip 가능
- OCR 결과의 사업자번호 / 가맹점명 등은 PII로 분류 → 결과 만료 정책 + access log
- secrets_mask는 현 모듈 그대로 활용

### 9.4 관측성
- 구조화 로그 (JSON) — `core.common.demo_logger`를 OpenTelemetry 호환으로 확장
- 메트릭: 큐 길이, scenario 처리 시간, OCR 실패율, OpenRouter 폴백 발생률
- 트레이스: run_id가 모든 로그/메트릭에 attach

## 10. 검증 전략

Phase 2 패턴(TDD + cumulative project lock + 3-reviewer audit) 유지:

- **mypy --strict** 잠금 파일 set: Phase 3-A 진입 시 `core/backends.py`, `cases/_protocols.py` 추가. 끝나면 `web/*` 추가.
- **pytest baseline**: 현 539 + 4 skipped → Phase 3-A 끝 expected `~600` (DI 테스트 신규 + 기존 회귀 0).
- **3-reviewer audit**: Phase 3-B, 3-C 종료 시 R1(보안) / R2(아키) / R3(정직성) 병렬.
- **e2e smoke**: 매 phase 마지막에 case07 영수증 5장 / case04 Discord 1건 / case09 메일 1건 web 통과.

## 11. Risks

| # | Risk | 처방 |
|---|---|---|
| R1 | mlx_vlm.server 단일 인스턴스 직렬 → 동시 OCR 요청 SLA 위반 | OCR 전용 큐 + concurrency=1, 큐 길이가 N 초과면 frontend가 "대기 M초" 안내 |
| R2 | safe_mode contextvars 전환 시 기존 monkey patch 의존 테스트 회귀 | shim 기간 둠. 두 모드 공존 후 Phase 3-B 진입 시점에 mp 제거 |
| R3 | 패키지 분리 시 import path 변경으로 모든 case 깨짐 | shim 단계 + 자동화 codemod (`libcst`) |
| R4 | 외부 시연 데모 직전 mlx 콜드스타트 force_safe 발생 | runner.py에 `--warmup-blocking` 옵션 추가, web `POST /admin/warmup` |
| R5 | 외부 사용 게이트(0/2) 미충족 상태에서 Phase 3-A 강행 | retract 절차 명시 — README/CLAUDE/MEMORY 동시 갱신 + design doc §1에 일자 기록 |

## 12. 결정 미루기 (Phase 4 후보)

- 자체 모델 fine-tune (영수증 카테고리 분류기, 한국어 OCR 정확도 향상)
- 사내 vector DB + RAG (회의록/제안서 사내 룰 자동 적용)
- whisper 통합 (case10 deferred decision matrix per `specs/case10-whisper-decision.md`)
- HWPX 실시간 미리보기 재평가 (rhwp 후속 또는 LibreOffice headless)
- 모바일 (사진 업로드 → 영수증 OCR) — 사내 영업 직원용

## 13. 외부 사용 시나리오 (Phase 3 산출물의 검증 컨텍스트)

Phase 3-D1 Streamlit MVP가 끝난 직후 외부 미팅·강의에서 다음을 시연한다 (게이트 충족 동시 진행):

| 시나리오 | 화면 | 시간 |
|---|---|---|
| 영수증 50장 업로드 → 경비 엑셀 | drag&drop → SSE 진행바 → xlsx 다운로드 | 2분 |
| 세금계산서 10장 → 회계 CSV | 동일 + 사업자번호 검증 fail 강조 | 2분 |
| 거래처 견적 50건 → PDF + 메일 일괄 | form → 진행바 → output zip | 3분 |

이 3건이 외부 사용 추적표에 row append되면 게이트 충족 (3 ≥ 2).

## 14. Glossary

- **DI** — Dependency Injection. 현 monkey patch 대체.
- **SSE** — Server-Sent Events. 단방향 진행률 stream.
- **TTL** — Time-To-Live. 결과 만료.
- **G1~G5** — §2.2의 5개 깨지는 가정.
- **3-A~3-E** — Phase 3 sub-phase. Plan 문서 참조.
