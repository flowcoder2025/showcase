# CLAUDE.md — AX Showcase

이 워크스페이스는 **사무자동화 쇼케이스** 전용 프로젝트입니다. 고객 미팅·강의 시연 + 다음 컨설팅 프로젝트에서 import해 재사용할 코어 라이브러리.

원래 `/Volumes/포터블/AX/기획`에서 관리하다가 2026-05-01에 별도 디렉토리로 분리됨.

## 빠른 진입

```bash
cd /Volumes/포터블/AX/showcase && claude
# 새 세션에서:
/mem-resume   # memory/MEMORY.md + logs 자동 로드
```

## 디렉토리 구조

```
showcase/
├── packages/flowcoder-office-tools/  # 재사용 라이브러리 패키지 (uv workspace)
│   └── src/flowcoder_office_tools/
│       ├── common/            # config, demo_logger, timer, secrets_mask, safe_mode (v1+v2)
│       ├── excel/             # reader, merger, pivot, writer, validator
│       ├── messaging/         # discord, email (Gmail API + SMTP)
│       ├── docgen/            # template, word, pdf (npx tsx), hwpx, hwp_preview
│       ├── ocr/               # gemma (MLX), receipt, invoice, _mlx_server
│       ├── ai/                # client (OpenRouter + OpenAI dual), prompts, tasks
│       ├── backends/          # Protocol DI facade (MLX/OR/Discord/Gmail/Safe/Cached×3)
│       ├── _internal/         # _mask_recursive (외부 noexport, R1-C3)
│       ├── protocols.py       # ScenarioResult + Backends + serialize_result/as_display
│       └── progress.py        # ProgressEvent + rich_progress_adapter
├── cases/                # 얇은 시나리오 wrapper (case01~case10, 10/10 시연 가능)
├── web/                  # Streamlit MVP (127.0.0.1 + path traversal + size cap + TTL)
├── personas/             # AX상사 가상 회사·인물·시드 데이터
├── docs/                 # 시연 대본 (1/3/5분 × 8) + 60분 강의 노트
├── tests/                # 684 passed, 4 skipped (Phase 1 + 2 + 3 + dogfood/)
├── specs/                # 설계 + Phase plan + deviation/audit 결정 문서
├── memory/               # 프로젝트 상태·세션 로그 (mem-resume 진입점)
│   ├── MEMORY.md         # 본체 메모리 (프로젝트 상태)
│   ├── lessons.md        # 교훈
│   ├── critical-gaps.md  # 미해결 갭
│   └── logs/             # 일별 세션 로그
├── runs/                 # Streamlit run_id 격리 (gitignore — .gitkeep + 내부 ignore)
├── runner.py             # CLI 메뉴 / --check / --check --strict / --safe
└── .github/workflows/ci.yml  # macos × 3.11/3.12/3.13 + env -i dogfood smoke
```

`~/.claude/projects/-Volumes-----AX-showcase/memory` → `./memory` symlink로 글로벌 mem 스킬과 호환.

## 스택

- Python 3.11+ / uv / pandas / openpyxl
- AI: OpenRouter (openai SDK 호환), Ollama Gemma 4 (Phase 2 OCR)
- Messaging: discord-webhook (카카오 자동발송 금지)
- Test/Lint: pytest, ruff, mypy --strict (cumulative project lock)

## 핵심 규칙 (잊지 말 것)

1. **모듈 참조 호출 (legacy CLI 트랙)**: `from flowcoder_office_tools.ai import client; client.chat()` — `safe_mode.intercept(patch)` 인터셉트 호환 위해. **신규 Streamlit/외부 consumer 트랙**: `safe_mode_v2.safe_mode_scope(True)` ContextVar 직접 사용 (env mutation 0).
2. **단일 safe_mode 경계 (CLI 한정)**: `runner.py` 만 `safe_mode.intercept()` 호출. Streamlit (`web/app.py:118`) 은 `safe_mode_scope` ContextVar 트랙. **두 트랙은 boundary 가 분리** — caller-controlled scope 가 아니라 boundary 가 책임.
3. **AI provider dual (T48.2)**: `OPENROUTER_API_KEY` 우선 → `OPENAI_API_KEY` 폴백 → `force_safe()`. MODEL_PRIORITY (OpenRouter 3-chain backward compat) + OPENAI_MODEL_PRIORITY (gpt-4o-mini, gpt-4.1-mini).
4. **column_map 강제**: 엑셀 모듈은 column_map 인자 필수, 하드코딩 금지
5. **시연 직전 검증**: `uv run python runner.py --check --strict` (MLX E2B/E4B + Discord webhook ping). MLX 메모리 해제는 Streamlit sidebar "MLX OCR 서버 (메모리 관리)" expander (T48.3).
6. **TDD + cumulative lock**: 각 task 신규 파일은 mypy --strict 통과해야 다음 진입. tests/ 부채 ceiling 은 `test_test_tree_strict_debt_does_not_grow` 가 잠금 (103 errors / 13 files, T41.5+).
7. **단일 sanitizer 진입점 (R1-C1)**: Streamlit 결과 위젯은 `web/_render.py::render_result()` 만 통과 — 내부 `as_display()` 거친 dict 만 `st.*` 에 전달. raw `ScenarioResult` 직접 렌더 금지.
8. **subagent-driven workflow**: implementer + N.5 fixer per task. Phase 종료 시 3-reviewer 병렬 audit (R1 보안 / R2 아키 / R3 정직성).
9. **익명화**: 실고객 데이터 매핑은 1Password/age 외부 보관, 레포에는 `.no_real_data` sentinel만

## Phase 진행 상황 (2026-05-12 — Phase 3 v2.1.1 close)

- **Phase 1 ✅** (T1~T17 + T18): HEAD `95fea4f`, 83 passed.
- **Phase 2 ✅** (T0~T26): HEAD `b4e4628`, 507 passed / 3 skipped, source 52 clean. 10/10 시연. 5건 deviation 정직 disclose (case03↔05 swap, rhwp PoC 실패, case10 whisper deferral, DoD N6 partial, weasyprint dropped).
- **T27/T28 maintenance** (2026-05-08): MLX 백엔드 전환 + 좀비 0 보장. HEAD `cf76f50`, 539 passed.
- **Phase 3 ✅ v2.1.1 close** (2026-05-12, HEAD `0f36a7a`):
  - **Phase 3-A** T35~T41 — ScenarioResult + Backends Protocol DI + `safe_mode_v2` ContextVar + 10 scenario 정식화 + progress events
  - **Phase 3-Pkg** T42~T46 — `core/` → `packages/flowcoder-office-tools/` 이주 + `__all__` snapshot + `_internal/` 격리 + dogfood + CI matrix
  - **Phase 3-Web** T47~T50 — Streamlit MVP (127.0.0.1 lock + path traversal + size cap + TTL + `as_display()` single sanitizer)
  - **T51 close audit** — 3-reviewer 병렬, critical R2-C1 (Backends DI 약속 vs 실 구현 정합) 은 design retract framing 으로 흡수 (T-PHASE4-DI-1 backlog)
  - **T51.5 fixers** — `b9a1b50` total cap fail-early / `52cc3f7` SECRET_ENV_NAMES 21건
  - **테스트**: 684 passed, 4 skipped (+145 Phase 3 신규). mypy strict source 73 clean / tests/ ceiling 103/13.
  - **시연 가능**: 10/10 (case07/08 e2e + T48.3 메모리 통제).
  - **CI**: macos-latest × Python 3.11/3.12/3.13 + dogfood `env -i` smoke + SECRET_ENV_NAMES 21건 leak guard.
  - **외부 사용 게이트**: (1) 0/1 미충족 보존 (마감 2026-05-09 도과 정직 인정), (2) dogfood ✅. 라벨 = "import-ready 패키지 (외부 reviewer feedback 미수집 인정)" — design v2.1 §8.3.
- **Phase 4 (deferred)**: T-PHASE4-DI-1 (cases 라우팅 backends.* 전환, ~2d) 우선. swap 비용 ~1.5주 (audit 정정). 자세한 backlog: README.md "Phase 4 backlog" 섹션.

## 관련 외부 리소스

- 기획 워크스페이스 (사업/제안서/리서치): `/Volumes/포터블/AX/기획`
- 글로벌 인덱스 메모리: `~/.claude/projects/-Volumes-----AX---/memory/MEMORY.md` (프로젝트 이전 마킹 보존)

## 작업 시작 체크리스트 (다음 세션 — Phase 4 진입 또는 외부 시연)

```bash
cd /Users/jerome/AX/showcase
/mem-resume                                    # 컨텍스트 로드
git log --oneline -5                           # HEAD 0f36a7a 확인 (T51 audit)
uv run pytest -q                               # 684 passed, 4 skipped 재확인
uv run python runner.py --check --strict       # 시연 환경 점검 (MLX E2B/E4B + Discord)

# Phase 4 진입 시
cat specs/2026-05-12-phase3-audit.md           # close audit findings ★
cat README.md                                   # Phase 4 backlog + swap 비용 정정 표 ★
# 권장 진입 task: T-PHASE4-DI-1 (cases 라우팅 backends.* 전환) — design v2.1 §4.2-RETRACT 가 backlog 명시화

# 외부 시연 시
uv run streamlit run web/app.py                # 127.0.0.1 lock — 외부 노출 차단
# 시연 후: specs/phase2-external-usage-promise.md 추적표에 row append → status partially-fulfilled
```

**E4B 4bit weight (W1, 즉시 wins, 보류)**: 현재 bf16(7GB)으로 동작. `huggingface-cli download mlx-community/gemma-4-e4b-it-4bit` 후 symlink 갱신 시 case08 평균 8.7s → 3s 수준 기대. Phase 4 진입 또는 시연 직전 처리.
