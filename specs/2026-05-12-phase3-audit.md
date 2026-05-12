# Phase 3 Close — 3-Reviewer Audit (HEAD c197012)

**Date**: 2026-05-12
**Scope**: Phase 3-A (T35~T41) + Phase 3-Pkg (T42~T46) + Phase 3-Web (T47~T50) 누적
**Baseline**: pytest 683 passed / 4 skipped → 684 (T51.5-fix(web)), mypy strict source 73 files clean, ruff clean
**Method**: 3 subagent 병렬 dispatch (security-engineer / system-architect / general-purpose), read-only audit. Spec `2026-05-08-phase3-plan-v2.md::T51` prompt 본문 verbatim.

---

## 종합 Verdict

| 트랙 | 결과 | Critical | High | Medium | Low |
|---|---|---:|---:|---:|---:|
| **R1 보안** | GO-with-conditions | 0 | 3 | 6 | 8 |
| **R2 아키** | GO-with-conditions | **1** | 3 | 3 | 3 |
| **R3 정직성** | GO (Grade **A−**) | 0 | 0 | 2 | 2 |

**Phase 3 close**: 진행 가능. R2-C1 (design 약속 vs 실 구현 정합) 처방은 T52 close commit 에서 design retract framing 으로 흡수 — code rewire 옵션 대비 Phase 3 의도 (재사용 라이브러리 추출 + 사내 단일 user 데모) 와 더 정합.

**즉시 처치 commit**:
- `WI-T51.5-fix(web)` `b9a1b50` — R1-H2 `_TOTAL_UPLOAD_CAP_BYTES` fail-early
- `WI-T51.5-fix(dogfood)` `52cc3f7` — R1-M5 `SECRET_ENV_NAMES` 7건 보강

**T52 close commit 에 흡수**:
- R2-C1 — design v2.1 §4.2 "Backends DI = 외부 호출 격리 lock" 약속 retract framing
- 외부 사용 게이트 (1) 0/1 미충족 disclose (이미 promise.md 표기)
- Phase 4 backlog 정리

---

## R1 보안 audit — Critical 0 / High 3 / Medium 6 / Low 8

**Verdict**: GO-with-conditions

### Critical (0건)

해당 없음.

### High (3건)

| ID | 위치 | finding | 처리 |
|---|---|---|---|
| **R1-H1** | `.gitignore` | 루트 `.gitignore` 에 `runs/` 패턴 부재 | **False-positive** — `runs/.gitignore:1 *` (T49 fee9c97) 가 이미 내부 contents 전부 ignore. `runs/` 디렉토리 자체는 `.gitkeep` 으로 keep, 내부는 자동 ignore. audit 시점에 본 메커니즘 catch 누락. |
| **R1-H2** | `web/app.py:102-111` | `_TOTAL_UPLOAD_CAP_BYTES` (200MB) 가 `stream_save` *후* 검증 → fail-late, 마지막 파일 fully written 후 raise | **closed `b9a1b50`** — `stream_save(*, remaining_total)` 추가, fail-early. partial-file unlink. test 신규. |
| **R1-H3** | `.streamlit/config.toml` + `web/app.py:58-59` | per-file 50MB × N 가능 vs total 200MB cap 정합 | **부분 흡수** `b9a1b50` (fail-early 가 4 파일 × 50MB 시점 abort). cap 자체 정책 변경은 Phase 4. |

### Medium (6건, Phase 4 backlog)

| ID | 위치 | finding |
|---|---|---|
| R1-M1 | `web/_runs.py:124-133` | `cleanup_expired_runs` lock TOCTOU race (single-process 가정에서 safe) |
| R1-M2 | `web/_runs.py:38` | `_ACTIVE_RUNS` set 이 module-global — multi-process 시 무용 |
| R1-M3 | `_internal/sanitize.py:26-27` | dict KEY 가 `_mask_recursive` 미통과 (현 usage 에서 safe, future-proof 아님) |
| R1-M4 | `_internal/sanitize.py:25` | `bytes` 길이 노출 (length sidechannel, 현 usage 에서 N/A) |
| **R1-M5** | `tests/dogfood/dogfood_smoke.py:23-38` | SECRET_ENV_NAMES 14건 — Anthropic/GitHub/AWS/HF/Slack 누락 → **closed `52cc3f7`** (총 21건) |
| R1-M6 | `_mlx_server.py:36-38` | 개발자 home path 하드코딩 (외부 consumer 시 FileNotFoundError → force_safe fallback, 안전하지만 hardening 미흡) |

### Low (8건, monitoring / Phase 4 polish)

L1: `run.json` 절대경로 노출 risk · L2: `_mask_recursive` import-time attribute leak (의도된 격리) · L3: sub-module `_helper` 잔존 (T45 plan deviation 으로 disclose 완료) · L4: MLX `api_key="not-needed"` 하드코딩 · L5: download_button `key=` collision risk (동일 basename) · **L6**: `assert _ADDR` 가 `python -O` 시 silent skip (assert → raise 권장) · L7: extension allow-list 만 검증, content sniffing 부재 · L8: `safe_mode.py:86` sha1 (cache key, no preimage attack — sha256 일관성 polish).

### 영역별 결론 (PASS 6/6)

1. ScenarioResult sanitize 단일 진입점 — PASS (M3 future-proof only)
2. Streamlit listen + path traversal + size cap — PASS-with-conditions (H2 closed, H3 partial, M1/M2 single-process 가정 명시 필요)
3. `__all__` + `_internal/` + module-level `_helper` 차단 — PASS
4. CachedBackend fingerprint vs api_key 누출 — PASS
5. dogfood secret env 차단 + env -i wrapping — PASS-with-conditions (M5 closed)
6. Backend audit log contract — PASS

---

## R2 아키 audit — Critical 1 / High 3 / Medium 3 / Low 3

**Verdict**: GO-with-conditions

### Critical (1건)

**R2-C1**: Backends Protocol DI 가 10/10 case 에서 `_ =` 폐기 — design v2.1 §4.2 "Backends DI = 외부 호출 격리 lock" 약속 미실현

- **Evidence**: `cases/case0[1-9]_*/scenario.py`, `case10_*/scenario.py` 전부 동일 패턴: `_ = backends or (safe_backends() if is_safe() else default_backends())  # T40 wire-up` → return value 폐기.
- 실 외부 호출: module-level routing (e.g., `tasks.draft_email`, `discord.send_with_level`, `receipt.extract`, `invoice.extract`, `email_mod.send`).
- 영향:
  - design §4.2 "책임 분리 lock" (safe_mode_v2 = 상태만 / Backends DI = 외부 호출 격리) 가 형식적으로만 존재. 실 인터셉트는 여전히 `safe_mode.intercept(unittest.mock.patch)` 가 담당 (runner.py:327).
  - Phase 4 swap 비용 추정 "큐 ~1-2d Backends DI 덕에 actor 주입만" 의 전제 무너짐.
  - dogfood smoke 의 `FakeBackend` 주입 검증이 production code path 와 무관.

**처방 옵션 (T52 close 에서 결정)**:
- **(b) design retract framing** ← 권고. "Backends Protocol DI = facade scaffolded; cases routing via module-level external call (Phase 2 inherited); 진짜 swap-ability 는 Phase 4 cases 라우팅 migration 필요" 로 §4.2 정정 + Phase 4 backlog 에 "T-PHASE4-DI-1: 10 case 라우팅 → backends.ocr/ai/msg 전환" 추가.
- (a) cases 10건 라우팅 수정 (~2d, ripple effect): Phase 3 의도 (사내 단일 user 데모) 와 비례 미흡 — Phase 4 정식 진입 시점에 통합 처리 권장.

### High (3건)

| ID | 위치 | finding | 처리 |
|---|---|---|---|
| R2-H1 | `web/app.py` | `streamlit_progress_adapter` 정의만, wire 미실현 (T49 spec 명시 defer 됨) | Phase 4 (~0.25d) — `placeholder = st.empty(); progress_cb = streamlit_progress_adapter(placeholder)` `execute_case` 안에 wire. progress UI 결손 보존, 다음 시연 정직 disclose. |
| R2-H2 | `runner.py:309` | `os.environ["DEMO_SAFE"] = "1"` 직접 mutation (Web 트랙은 `safe_mode_scope` ContextVar) | Phase 4 — legacy CLI 호환 위해 보존, 외부 consumer 가 mimic 하지 않도록 docstring/README 에 명시 |
| R2-H3 | `tests/dogfood/pyproject.toml:11` | `flowcoder-office-tools` bare name dependency → 외부 git+ssh fetch 호환성 untested | Phase 4 — 외부 사용 게이트 (1) 미충족 상태와 동일한 시그널. `git+ssh://` smoke 추가는 외부 reviewer 첫 import 시점에 자연 catch 가능 |

### Medium (3건)

R2-M1: `extras` dict 가 case 별 비대칭 (dump bag 경계, design v2.1 부록 A 매트릭스 허용) · R2-M2: dogfood install 순서 implicit ordering (`--no-index` 권장) · R2-M3: `safe_mode` v1 + v2 듀얼 (CLI v1+v2 / Web v2-only) — docs 에 명시 권장.

### Low (3건)

L1: `backends.protocols` re-export 중복 · L2: `_DefaultMessagingBackend.cache_identity()` Discord+Gmail concat (캐시 효율 미세 손실) · L3: `cleanup_expired_runs` 매 page-load (single-process safe).

### Phase 4 swap 비용 정정 (design v2.1 §0.1 표)

| swap | 원 추정 | 정정 | 사유 |
|---|---|---|---|
| FastAPI 라우트 | ~2-3d | ~2.5-3.5d | H1 wiring +0.5d |
| 큐 (Dramatiq+Redis) | ~1-2d | **~2-3d** | C1 — cases 라우팅 변경 동반 |
| DB | ~3-4d | ~3-4d | 정합 (serialize_result JSON 호환) |
| Next.js | ~1주 | ~1주 | 정합 (as_display 단일 sanitizer JSON 환원 가능) |
| whisper/fine-tune backend | (미언급) | +0.5-1d for routing migration first | C1 영향 |

**총 swap 비용**: design §0.1 ~1주 → **~1.5주** (cases 라우팅 변경 흡수).

### 영역별 결론

1. Layer 의존 방향 — PASS (역방향 0건, shim 제거 완전)
2. Backends DI ↔ safe_mode_v2 책임 분리 — **FAIL** (C1)
3. ScenarioResult universality — PASS (M1 with extras dump bag 경계)
4. uv workspace + path dep — PASS-with-conditions (H3 외부 git+ssh untested)
5. shim 제거 후 잔존 — PASS (production 0건, docstring 2건 cosmetic)
6. progress_cb 호환성 — **FAIL** (H1 wire 미실현)
7. Phase 4 swap 비용 — GO-with-conditions (C1 정정 시점에 큐/whisper 추정 보정)

---

## R3 정직성 audit — Critical 0 / High 0 / Medium 2 / Low 2 / Grade **A−**

**Verdict**: GO

### Grade A− 사유

- design v2.1 의 모든 critical / high 약속 (sanitizer 단일 진입점 / Streamlit 보안 / underscore 격리 / TTL owner / ScenarioResult universality / Layer 단방향) **전건 코드 흡수**
- Plan example hallucination 4건 (T44 `read_excel`, T45 helper 격리 강·약 해석, T46 dogfood import, T49 ProgressEvent attribute access) **모두 commit body 또는 lessons.md 에 정직 disclose**
- Test 카운트 라벨링 round 0건 — design minimum 합 80 vs 실 140 (=37+43+11+10+12+12+3+7+5 신규), **1.75x 초과**
- 외부 사용 게이트 0/1 미충족 — T34.5 `a91d351` 정직 인정, dogfood 가 (1) 대체로 라벨링되지 않음
- lessons.md 가 commit history 와 사실상 1:1 정합

### A− mild gap (close 진행에 무관)

- **R3-M1**: public API surface tests 3 vs design minimum ≥5. 의도(R1-C3 surface lock + helper deny-list + snapshot drift) 충족, 라벨링 round 회피.
- **R3-M2**: dogfood "≥10" framing 모호 — pytest 카운트 vs smoke script assertion 단위 mismatch.
- **R3-L1**: T48 commit body deviation 단독 disclose 부족 (MEMORY.md 보강 의존).
- **R3-L2**: design v2.1 §5.4 line 308 "scenario sigchg 회귀 보강 ≥20" 표현이 G5 포함 의도 모호.

### 영역별 결론 (PASS 5/5)

1. design v2.1 약속 vs 실제 코드 정합 — PASS (17/17 약속 흡수)
2. Test 카운트 minimum — PASS (140 vs 80, 1.75x)
3. Plan example hallucination — PASS (4건 전건 disclose)
4. 외부 사용 게이트 — PASS (0/1 정직 인정, dogfood 대체 라벨 회피)
5. lessons.md / commit history 정합 — PASS (mild gap 1건: T35/T40 lesson 부재 — strong-disclosure 회피로 정직성 손상 아님)

---

## Phase 3 close 권고 (T52)

1. **MUST**: R2-C1 design retract framing — design v2.1 §4.2 "책임 분리 lock" 약속을 "facade scaffolded for Phase 4" 로 정정. Phase 4 backlog 에 "T-PHASE4-DI-1: 10 case 라우팅 → backends.* 전환" 추가.
2. **MUST**: 외부 사용 게이트 0/1 미충족 disclose — `specs/phase2-external-usage-promise.md` 추적표에 명시적 row (이미 expired-without-fulfillment 라벨링 완료).
3. **SHOULD**: Phase 4 backlog 정리 — R1 (M1/M2/M3/M6/L6/L7/L8/H1 root .gitignore docs polish), R2 (H1/H2/H3/M1/M2/M3), R3 (M1/M2 docs polish).
4. **SHOULD**: README/CLAUDE/MEMORY 갱신 — Phase 3 v2.1 close 명시, dogfood + sanitize + 보안 surface 강조, Phase 4 swap 비용 정정 표 반영.
5. **MAY**: T48 deviation MEMORY.md 보강이 commit body 단독 disclose 부족을 보완 — Phase 4 commit 부터는 body 자체에 충분한 deviation enumeration 권고.

---

## 메타 정보

- **R1 prompt**: spec line 2675~2697 verbatim
- **R2 prompt**: spec line 2699~2719 verbatim
- **R3 prompt**: spec line 2721~2738 verbatim
- **Spec deviation (audit prompt 자체)**: R1 prompt 의 audit doc 파일명 변수 `2026-05-XX-phase3-audit.md` → `2026-05-12-phase3-audit.md` (실 작성일 2026-05-12).

### Subagent 출력 raw (요약 발췌)

R1, R2, R3 각 subagent 의 전체 출력은 본 commit (T51) 의 사전 turn 에서 spec 본문 verbatim 으로 dispatch 한 결과. 본 audit doc 은 그 출력을 단일 narrative 로 통합. critical/high 결정은 본 doc 의 categorization 기준 (T51.5 fixer commit 으로 closed / T52 docs 처리 / Phase 4 backlog) 으로 재라벨링됨.
