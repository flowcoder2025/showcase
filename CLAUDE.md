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

## Phase 진행 상황 (2026-05-02 — Phase 2 종료)

- **Phase 1 ✅ 완료**: 17/17 tasks + T18 cleanup. HEAD `95fea4f`, 83 passed.
- **Phase 2 ✅ 완료**: T0~T26 (Group A~H + DoD + 3-reviewer audit + cleanup + docs).
  - HEAD `b4e4628` (T25 audit cleanup), T26은 docs-only close commit
  - 테스트: **507 passed, 3 skipped** (Phase 1 baseline 83 + Phase 2 신규 424)
  - Production lock (`mypy --strict core/ runner.py cases/`): **52 source files clean**
  - tests/ mypy 부채: **65 errors / 8 files** (Phase 1 legacy, ceiling locked)
  - 시연 가능: **10/10** 케이스 (case01~case10)
  - 진행 순서 (Plan v2 Deviation 1 swap 반영): **04 → 05 → 03 → 07 → 10 → 08 → 06** (case03이 case05 PDF 모듈에 의존)
  - 5건 deviation: case03↔case05 swap, rhwp PoC 실패 (Phase 3 deferred), case10 whisper deferral, DoD §13 N6 partially passed, weasyprint 폴백 dropped
- **Phase 3 🔒 게이트**: 외부 사용 2회 이상 (현재 0/2, 하드 마감 **2026-05-09**) → 피드백 반영 후 진입
  - 후보: rhwp 재평가, 실 영수증 hold-out, whisper 통합, safe_mode dummy 통일, excel reader 헬퍼, tests/ 부채 정리, weasyprint/reportlab 평가
  - 자세한 backlog: `README.md` Phase 3 섹션

## 관련 외부 리소스

- 기획 워크스페이스 (사업/제안서/리서치): `/Volumes/포터블/AX/기획`
- 글로벌 인덱스 메모리: `~/.claude/projects/-Volumes-----AX---/memory/MEMORY.md` (프로젝트 이전 마킹 보존)

## 작업 시작 체크리스트 (다음 세션 — Phase 3 또는 외부 사용)

```bash
cd /Volumes/포터블/AX/showcase
/mem-resume                                    # 컨텍스트 로드
git log --oneline -5                           # HEAD T26 확인
uv run pytest -q                               # 507 passed, 3 skipped 재확인
uv run python runner.py --check --strict       # 시연 환경 점검
```

**Phase 3 진입 전 외부 사용 2회 이상 충족 필요** — `specs/phase2-external-usage-promise.md` 추적표에 일자/청중/관찰 row append.
