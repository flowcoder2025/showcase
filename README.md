# AX Showcase

사무자동화 쇼케이스 — 고객 미팅·강의 시연 + 실전 재사용 모듈.

## Setup

```bash
uv sync
cp .env.example .env  # API 키 입력
```

## Usage

```bash
# 메뉴 모드 (시연용)
uv run python runner.py

# 환경 점검 (시연 직전 필수)
uv run python runner.py --check

# 안전 모드 (외부 API 미호출)
DEMO_SAFE=1 uv run python runner.py case09
```

## Structure

- `core/` — 재사용 라이브러리 (CLI 무관)
- `cases/` — 시나리오 wrapper
- `personas/` — AX상사 가상 회사·인물·샘플 데이터
- `docs/` — 시연 대본·강의 노트

자세한 설계: `/Volumes/포터블/AX/기획/specs/ax-showcase/2026-04-30-design.md`

## Phase 1 Status

✓ Foundation + 코어 인터페이스 검증 완료
- `core/`: common (config, logging, timer, secrets_mask, safe_mode), excel (reader, merger, pivot, writer, validator), ai (client, prompts, tasks), messaging (discord)
- `cases/`: case01, case02, case09
- DoD 통과: column_map 재사용, OpenRouter 폴백, safe_mode 격리, secrets 마스킹, deterministic safe 캐시

다음 단계: Phase 2 (case03~10 양산). case06 진입 전 rhwp PoC 필수.

## Phase 2 Status (T25 시점)

진행 중 — 8/10 케이스 시연 가능 (case01/02/03/04/05/07/09/10), case06/08 마무리 단계.

**Production lock (mypy --strict)**: `core/` + `runner.py` + `cases/` 51 파일 clean.

**알려진 부채 (R3-H1 disclosure)**:
- `tests/` 디렉토리는 cumulative mypy --strict 잠금 범위 외 — 65 errors / 8 files
  존재. T25 audit 시점에 ceiling으로 잠가 더 이상 늘지 않도록 회귀 가드만
  추가했으며, 점진적 정리는 Phase 3 또는 별도 cleanup task 범위.
- T26 단계에서 README/MEMORY.md를 Phase 2 종료 기준으로 갱신 예정.
