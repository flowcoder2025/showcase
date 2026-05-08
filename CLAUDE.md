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
├── core/                # 재사용 라이브러리 (CLI 무관)
│   ├── common/          # config, logging, timer, safe_mode, secrets_mask
│   ├── excel/           # reader, merger, pivot, writer, validator
│   ├── ai/              # client (OpenRouter + 폴백), prompts, tasks
│   └── messaging/       # discord webhook
├── cases/               # 얇은 시나리오 wrapper (case01~case10, 10/10 시연 가능)
├── personas/            # AX상사 가상 회사·인물·시드 데이터
├── docs/                # 시연 대본 (1/3/5분 × 8) + 60분 강의 노트
├── tests/               # 507 passed, 3 skipped (Phase 1 + 2)
├── specs/               # 설계 + Phase plan + deviation 결정 문서
├── memory/              # 프로젝트 상태·세션 로그 (mem-resume 진입점)
│   ├── MEMORY.md        # 본체 메모리 (프로젝트 상태)
│   ├── lessons.md       # 교훈
│   ├── critical-gaps.md # 미해결 갭
│   └── logs/            # 일별 세션 로그
└── runner.py            # 메뉴 / --check / --check --strict / --safe
```

`~/.claude/projects/-Volumes-----AX-showcase/memory` → `./memory` symlink로 글로벌 mem 스킬과 호환.

## 스택

- Python 3.11+ / uv / pandas / openpyxl
- AI: OpenRouter (openai SDK 호환), Ollama Gemma 4 (Phase 2 OCR)
- Messaging: discord-webhook (카카오 자동발송 금지)
- Test/Lint: pytest, ruff, mypy --strict (cumulative project lock)

## 핵심 규칙 (잊지 말 것)

1. **모듈 참조 호출**: `from core.ai import client; client.chat()` (✓), `from core.ai.client import chat` (✗) — safe_mode patch 인터셉트 위해
2. **단일 safe_mode 경계**: `runner.py`만 `safe_mode.intercept()` 호출. 시나리오/케이스는 thin wrapper, 자체 wrap 금지
3. **OpenRouter 폴백 체인**: Gemini 2.5 Flash → Claude Haiku 4.5 → GPT-4o-mini → `force_safe()`
4. **column_map 강제**: 엑셀 모듈은 column_map 인자 필수, 하드코딩 금지
5. **시연 직전 검증**: `uv run python runner.py --check --strict` (Ollama + Discord webhook ping 포함)
6. **TDD + cumulative lock**: 각 task 신규 파일은 mypy --strict 통과해야 다음 진입
7. **subagent-driven workflow**: implementer + N.5 fixer per task. Phase 종료 시 3-reviewer 병렬 audit
8. **익명화**: 실고객 데이터 매핑은 1Password/age 외부 보관, 레포에는 `.no_real_data` sentinel만

## Phase 진행 상황 (2026-05-08 — T28 MLX 백엔드 전환 완료)

- **Phase 1 ✅ 완료**: 17/17 tasks + T18 cleanup. HEAD `95fea4f`, 83 passed.
- **Phase 2 ✅ 완료**: T0~T26 (Group A~H + DoD + 3-reviewer audit + cleanup + docs).
  - 테스트: **507 passed, 3 skipped** (Phase 1 baseline 83 + Phase 2 신규 424)
  - Production lock: 52 source files clean
- **T27/T28 (Maintenance, 2026-05-08)**: case10 whisper deferral 결정 문서 복원 + Ollama → MLX(mlx_vlm.server OpenAI-호환) 백엔드 전환.
  - HEAD `cf76f50` (T28). 좀비 0 보장(Popen `start_new_session=True` + atexit/SIGTERM/SIGINT/SIGHUP → killpg SIGTERM→5s grace→SIGKILL).
  - 테스트: **539 passed, 4 skipped** (T26 + 신규 32 회귀 0). mypy --strict source: **53 files clean**.
  - 시연 가능: **10/10** (case07/08 e2e 검증: 88/100 + 28/30, 좀비 회수 확인).
  - 외부 사용 게이트는 변동 없음 — 본 작업은 maintenance.
- **Phase 3 🔒 게이트**: 외부 사용 2회 이상 (현재 0/2, 하드 마감 **2026-05-09**) → 피드백 반영 후 진입.
  - **설계 + 플랜 (2026-05-08)**: `specs/2026-05-08-phase3-design.md` (전체 설계, 깨지는 5개 가정 G1~G5 처방, target 아키, layer 책임), `specs/2026-05-08-phase3-plan.md` (T29~T52 task map, 즉시 wins W1~W3, 패키징 P1~P3).
  - **다음 세션 첫 명령**: 게이트 상태 확인 → 충족/retract 결정 → Phase 3-A T29부터 시작.

## 관련 외부 리소스

- 기획 워크스페이스 (사업/제안서/리서치): `/Volumes/포터블/AX/기획`
- 글로벌 인덱스 메모리: `~/.claude/projects/-Volumes-----AX---/memory/MEMORY.md` (프로젝트 이전 마킹 보존)

## 작업 시작 체크리스트 (다음 세션 — Phase 3-A 진입 또는 외부 사용)

```bash
cd /Users/jerome/AX/showcase
/mem-resume                                    # 컨텍스트 로드
git log --oneline -5                           # HEAD T28 확인 (cf76f50)
uv run pytest -q                               # 539 passed, 4 skipped 재확인
uv run python runner.py --check --strict       # 시연 환경 점검 (MLX E2B/E4B 포함)

# Phase 3 진입 결정
cat specs/phase2-external-usage-promise.md     # 게이트 0/2 → 진입 결정
cat specs/2026-05-08-phase3-design.md          # 설계 ★
cat specs/2026-05-08-phase3-plan.md            # task map (T29~T52) ★
```

**Phase 3-A 진입 전 의사결정**: 외부 사용 ≥2/2 충족 또는 production-ready 주장 명시 retract. plan §1 진입 절차 참조.

**E4B 4bit weight (W1, 즉시 wins)**: 현재 bf16(7GB)으로 동작. `huggingface-cli download mlx-community/gemma-4-e4b-it-4bit` 후 symlink 갱신 시 case08 평균 8.7s → 3s 수준 기대.
