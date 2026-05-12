---
name: AX Showcase 사무자동화 케이스 쇼케이스
description: 고객 미팅·강의 시연용 사무자동화 케이스 10건 + 실전 재사용 코어 모듈 라이브러리
type: project
originSessionId: 5f17504f-aeae-4369-a83b-4a0ef76e757b
---
# AX Showcase

사무자동화 케이스를 모듈 단위로 정리해 (1) 고객 미팅·강의 라이브 시연, (2) 다음 컨설팅 프로젝트에서 import해 재사용하는 두 목표를 동시에 달성하는 프로젝트.

**Why**: AX 컨설팅 미팅·강의에서 "이런 거 됩니다" 보여줄 임팩트 자산이 부족했고, 매 컨설팅마다 같은 엑셀·메일·OCR 모듈을 새로 짜는 비효율을 끊기 위함.

**How to apply**: AX 컨설팅·제안 작업 중 사무자동화 시연이 필요할 때 또는 다음 프로젝트에서 엑셀/메일/OCR/AI 모듈이 필요할 때 이 레포의 `packages/flowcoder-office-tools/` (T43 이주 후) 를 import. 진행 상태·다음 단계는 아래 참조.

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

## 진행 상태 (2026-05-12 — **Phase 3 v2.1.1 ✅ close (T52)**)

- **HEAD**: `0f36a7a` (T51 audit) — T52 docs commit 으로 close 마무리 예정 (본 commit body 참조)
- **테스트**: **684 passed, 4 skipped** (T50 683 → T51.5 +1 = 684. Phase 2 baseline 539 → +145 Phase 3 누적)
- **Production lock (mypy --strict)**: 73 source files clean (`packages/flowcoder-office-tools/src/ + runner.py + cases/ + web/`)
- **tests/ 부채 (mypy --strict)**: **103 errors / 13 files** — T41.5 ceiling 유지. `test_test_tree_strict_debt_does_not_grow` 가 lock.
- **ruff** clean. **CI matrix** macos-latest × Python 3.11/3.12/3.13 + `env -i` dogfood smoke + SECRET_ENV_NAMES 21건 leak guard (T51.5 보강).
- **시연**: 10/10. AI dual provider (OPENROUTER → OPENAI 폴백, T48.2). MLX 메모리 통제 sidebar (T48.3).
- **외부 사용 게이트**: (1) 0/1 미충족 보존, (2) dogfood ✅. 라벨 = "import-ready 패키지 (외부 reviewer feedback 미수집 인정)" — design v2.1 §8.3.

### T49~T52 — Phase 3-Web 마감 + close audit (2026-05-12, 6 commits)

| Task | Commit | 변경 | 비고 |
|------|--------|------|------|
| T49 | `561d07f` | `web/_progress.py` Streamlit adapter (모듈만, plumb defer) + `web/_render.py` `render_result` 단일 sanitizer (R1-C1) + `runs/.gitignore` + TTL start hook | spec deviation 5건 disclose (ProgressEvent attribute→dict, zip-매칭, dead code 제거, Mapping 시그니처, 시각 검증 T50 흡수) |
| T50 | `c197012` | `tests/test_streamlit_smoke.py` 5 tests (app import / run dir 격리 / **R1-C1 sentinel `ya29.*` leak 0 검증** / safe-mode 라운드트립 / 10-case schema 커버리지) | spec deviation: case01 → case09 (`incoming_message` config hermetic) |
| T51 | `0f36a7a` | 3-reviewer 병렬 audit (R1/R2/R3) → `specs/2026-05-12-phase3-audit.md` | R1 critical 0/high 3 · R2 critical **1** (Backends DI `_ =` 폐기 → design retract framing T52) · R3 critical 0/high 0/Grade **A−** |
| T51.5-fix(web) | `b9a1b50` | `_TOTAL_UPLOAD_CAP_BYTES` fail-early — `stream_save(*, remaining_total)` + partial unlink + 신규 test | R1-H2 흡수 |
| T51.5-fix(dogfood) | `52cc3f7` | SECRET_ENV_NAMES 14 → 21 (Anthropic/GitHub/AWS/HF/Slack 보강) | R1-M5 흡수 |
| T52 | (본 commit) | design v2.1 §4.2-RETRACT framing + README/CLAUDE/MEMORY + Phase 4 backlog + promise.md row | R2-C1 design retract, swap 비용 ~1주→~1.5주 정정 |

**Phase 3 audit (T51) 핵심 finding**:
- **R2-C1**: 10/10 case 가 `_ = backends or (safe_backends() if is_safe() else default_backends())` 패턴으로 backends 인자를 폐기. 실 외부 호출은 module-level routing (`tasks.draft_email`, `discord.send_with_level`, `receipt.extract` 등). design v2.1 §4.2 "Backends DI = 외부 호출 인터셉트·격리 담당" 약속은 facade scaffolded 수준. T52 design retract framing + T-PHASE4-DI-1 backlog 명시화.
- **R1-H1 false-positive**: `runs/.gitignore:1 *` (T49 fee9c97) 가 이미 contents 전부 ignore — audit 시 catch 누락.
- **Phase 4 swap 비용 정정**: design §0.1 ~1주 → **~1.5주** (T-PHASE4-DI-1 cases 라우팅 변경 흡수).

### Phase 3 commit history (상세는 git log + memory/logs/ 참조)

- **Phase 3-A** (T34.5~T41.6, 11 commits, 2026-05-10~11) — protocols + backends DI + safe_mode_v2 + 10 scenario 정식화 + progress events + cwd-coupling 제거. Phase 3-A 종료 HEAD `bdd1489`. T41.5 ceiling lock 103/13 정착. T41.6 caller-controlled scope vs boundary 책임 lesson (force_safe Token leak 차단).
- **Phase 3-Pkg** (T42~T46, 6 commits, 2026-05-11) — uv workspace scaffold → libcst codemod 이주 → py.typed marker → meta path finder shim → `__all__` snapshot + `_internal/` 격리 → shim 제거 + dogfood + CI matrix. Phase 3-Pkg 종료 HEAD `c327ab9`.
- **Phase 3-Web** (T47~T50, 8 commits, 2026-05-12) — Streamlit MVP 골격 → button label 정렬 → input form + run_id 격리 → sys.path 호환 → AI dual provider → MLX manual shutdown UI → progress adapter + render_result single sanitizer + TTL hook → smoke tests. Phase 3-Web 종료 HEAD `c197012`.
- **Phase 3 close** (T51, T51.5×2, T52, 2026-05-12) — 3-reviewer audit + fail-early cap + SECRET_ENV_NAMES 21건 + design retract framing. T52 본 commit.

핵심 lessons (lessons.md 참조):
- `py.typed` marker 누락 = import-untyped 부채 폭증 (T43.5)
- meta path finder: `__getattr__` 는 sub-sub deep import 미지원, `sys.meta_path.insert(0, ...)` 필요 (T44)
- spec example 의 helper 격리 강·약 해석 — 강한 해석(physical move) vs 약한 해석(grep + surface test) (T45)
- 외부 consumer dogfood 가 extras 누락 (lxml) 을 즉시 catch — workspace install ≠ extras 그래프 (T46)
- long-running UI subprocess weight-warm 정책은 사용자 통제 surface 필수 (T48.3 — 90GB mlx_vlm 사건)
- caller-controlled scope ≠ caller token reset — boundary 책임 lock 이 더 안전 (T41.6)
- spec example 의 stale import 는 surface lock (T45) 후 일괄 sweep 필요 (T49 ProgressEvent attribute access — TypedDict 정정)

### 외부 사용 게이트 (T34.5 → T52)

- **하드 마감 2026-05-09 도과** (T52 close 시점 +3일). 0/1 미충족 인정 — 약속은 보존.
- production-ready 라벨 retracted (T32). Phase 3 진입 = 옵션 (a) 사내 데모 + dogfood ✅ (T46 + T51.5 보강) — design v2.1 §5.1 "추가 검증, 대체 아님".
- 향후 외부 시연 시 `specs/phase2-external-usage-promise.md` 추적표에 row append → `partially-fulfilled (1+/?)` 갱신. 추가 연장 마감일 두지 않음.

### Phase 4 backlog (T52 정리)

자세한 list 는 README.md "Phase 4 backlog" 섹션 참조. 핵심 우선순위:

1. **T-PHASE4-DI-1** (~2d, ripple) — 10 case module-level 호출 → `backends.ocr/ai/msg.*` 라우팅. 동반: `runner.py:309` env mutation → `safe_mode_scope` 통일. design §4.2-RETRACT 가 backlog 명시화. **이 task 가 swap-ability 의 진짜 lock — Phase 4 진입 첫 task 권장.**
2. **T-PHASE4-WEB-1** (~0.25d) — Streamlit progress adapter wire-up (R2-H1, 모듈만 존재, plumb 미실현)
3. **T-PHASE4-WEB-2~4** — multi-process safety / total cap 정합 / `assert _ADDR` → raise (R1-M1/M2/H3/L6)
4. **T-PHASE4-PKG-1** — 외부 git+ssh 호환 smoke (R2-H3) — 외부 reviewer 첫 import 시점에 자연 catch 가능
5. **T-PHASE4-OCR-1 / WHISPER-1 / RHWP-1~3** — Phase 2 deferred (case07/08/10/06)
6. **T-PHASE4-DEBT-1** tests/ mypy strict 103 → 0 점진 정리

**즉시 wins 보류** (W1 E4B 4bit / W2 few-shot / W3 `--warmup-blocking`) — 시연 직전 우선 처리.

---

## Phase 1/2 + T27/T28 + Phase 3 설계 (historical, 자세한 내용은 README.md / git log / memory/logs/ 참조)

- **Phase 1 ✅** (T1~T17 + T18 cleanup, 2026-04-?? ~ 05-01) — Foundation + case01/02/09. HEAD `95fea4f`, 83 passed.
- **Phase 2 ✅** (T0~T26, 2026-05-01 ~ 05-02) — case03~10 양산 + DoD + 3-reviewer audit + cleanup. HEAD `b4e4628`. 507 passed / 3 skipped. 5건 deviation 정직 disclose (case03↔05 swap, rhwp PoC 실패, case10 whisper deferral, DoD N6 partial, weasyprint dropped).
- **T27/T28 maintenance** (2026-05-08) — case10 whisper deferral 결정 문서 복원 + Ollama → MLX(mlx_vlm.server) 백엔드 전환 (좀비 0 보장: Popen `start_new_session=True` + atexit/SIGTERM/SIGINT/SIGHUP → killpg). HEAD `cf76f50`. 539 passed.
- **Phase 3 설계 v1 → v2 → v2.1** (2026-05-08) — v1 SaaS 방향, v2 재사용 우선, v2.1 audit 17건 finding 반영. active: `specs/2026-05-08-phase3-design-v2.md` (commit `b5ffe0f`). 게이트: (1) 외부 사용 보존 + (2) dogfood 추가 검증.

## 다음 세션 진입 (Phase 4 또는 외부 시연)

```bash
cd /Users/jerome/AX/showcase && claude
/mem-resume
git log --oneline -10                          # HEAD T52 close 확인
uv run pytest -q                               # 684 passed, 4 skipped
uv run python runner.py --check --strict       # 시연 환경 점검

# Phase 4 진입 권장 entry task
cat specs/2026-05-12-phase3-audit.md           # R2-C1 design retract → T-PHASE4-DI-1 ★
cat README.md                                   # Phase 4 backlog + swap 비용 정정 표 ★

# 외부 시연 시
uv run streamlit run web/app.py                # 127.0.0.1 lock
# 시연 후: specs/phase2-external-usage-promise.md 추적표 row append
```

**Phase 3 close 핵심 baseline**:
- HEAD: T52 docs commit (본 commit)
- pytest 684 passed / 4 skipped, mypy strict source 73 clean, tests/ ceiling 103/13
- CI matrix 활성화 / SECRET_ENV_NAMES 21건 / dogfood smoke 영구 게이트
- 10/10 시연 가능, AI dual provider, MLX 메모리 통제 UI

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
