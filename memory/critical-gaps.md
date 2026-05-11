---
name: AX Showcase Critical Gaps
description: AX Showcase 미해결 갭 / 결정 대기 / 후속 task 추적
type: project
---
# Critical Gaps — AX Showcase

미해결 이슈·결정 대기 사항. 해소 시 제거.

## Phase 3-A ✅ 종료 (2026-05-11, T35~T41 + T41.5 정합) + Phase 3-Pkg T42~T45 ✅

T35~T38 완료, T39~T41 완료, T41.5 부채 정합 완료. Phase 3-Pkg T42~T45 진행 중 — 다음은 T46 (shim 제거 + dogfood fixture + CI matrix).

### ~~1. safe_mode_v2 force_safe Token 미reset 호출자 3곳~~ ✅ 해결 (2026-05-11, post-T41.5)
- ~~gemma/client/email 의 force_safe 호출 후 token discard → cross-case leak~~
- 정합 방향: caller (각 호출자) 가 reset 하는 대신 **`safe_mode.intercept` boundary** 가 entry-time 값을 `safe_mode_scope` 로 lock. case 종료 시 자동 복원.
- 회귀 차단: `tests/test_safe_mode_v2.py::test_intercept_boundary_isolates_force_safe_between_cases`
- Token return contract 는 보존 (명시적 scope 필요한 caller 용 — 현 호출자는 sticky failover 의도로 discard).

### 2. dogfood fixture CI 미활성화
- design v2.1 §5.1: dogfood = 추가 검증 트랙 (외부 사용 약속의 대체 아님)
- **T46에서 영구 PR merge 차단 조건으로 활성화 예정** (T45 surface lock 완료 → T46 shim 제거와 같이 진행)
- 현재 0% 진행 — Phase 3-Pkg T46 단계에서 구축

### 3. tests/ mypy strict 부채 ceiling 잠금 (T41.5 새로 명문화)
- 현 ceiling: **103 errors / 13 files** (`tests/test_test_tree_strict_debt_does_not_grow.py`)
- 부채 줄이려면: legacy fix → CEILING_TOTAL_ERRORS / CEILING_AFFECTED_FILES 같이 내림
- 부채 늘려야 하면: 별도 commit 으로 ceiling 갱신 + 사유 명시 (무계획 누적 차단)
- Phase 1 legacy 8 files 부채 + Phase 2 신규 5 files 부채 — Phase 3 backlog

## Phase 2 잔여 (Phase 3 backlog)

### 4. rhwp PoC fallback 미해결
- Phase 2 T16 5옵션 평가 모두 실패 → `specs/rhwp-poc-decision.md` 결정 문서로 Phase 3 deferred
- T-PHASE3-RHWP-1/2/3 (rhwp v2 prebuilt / HOP CLI / LibreOffice 24+) 후보

### 5. DoD §13 N6 — 실 영수증 10장 hold-out 미수행
- 합성 영수증 self-OCR 자기충족 위험 (R2-M2)
- T-PHASE3-OCR-1 후보. `specs/dod-n6-decision.md`에 partially passed 라벨

### 6. case10 whisper 음성 입력 미구현
- Phase 2는 텍스트 입력만. `specs/case10-whisper-decision.md`에 Phase 3 deferred
- T-PHASE3-WHISPER-1 후보 (openai-whisper / OpenRouter audio / macOS Speech)

### 7. weasyprint vs reportlab 폴백 미평가
- Phase 2 T5: Pango/Cairo 의존성 OSError → md-to-pdf (npx tsx)만 사용
- 다음 컨설팅 프로젝트에서 docgen 재사용 시 재검토 (T-PHASE3-DEBT-4)

### 8. `core/excel/reader.read_excel(column_map=...)` 헬퍼 부재
- 다중 case에서 `pd.read_excel` + 내부 column_map 적용 패턴 중복
- T-PHASE3-DEBT-2 (Phase 3-Pkg 추출 시 다룸)

## 환경 점검 체크리스트 (시연 직전 필수)

- `OPENROUTER_API_KEY` (실제 시연 시)
- `DISCORD_WEBHOOK_URL` (실제 시연 시)
- MLX 두 모델 (E2B 11437 / E4B 11438) — `runner.py --check --strict`로 사전 ping
- `npx` + md-to-pdf 스킬 (case05/06)
- Gmail OAuth 또는 SMTP credentials (case03)
- HWPX 정부지원사업 양식 라이선스 확인 (case06)
- sample_data 생성 (`uv run python personas/sample_data/generate.py`)
