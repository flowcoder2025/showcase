"""tests/ mypy --strict 누적 부채 ceiling lock (T41.5 — 2026-05-11).

배경:
- production layer (`core/` + `runner.py` + `cases/`) 는 mypy --strict 0 errors
  cumulative project lock 유지 중 (현재 65 source files clean).
- tests/ 는 Phase 1 legacy + Phase 2 합성 fixture 등으로 누적 부채 존재.
- MEMORY.md 가 "ceiling locked by `test_test_tree_strict_debt_does_not_grow`"
  라고 기록했지만 실제로 그 test 가 부재한 채 부채가 무방어로 늘어남
  (Phase 2 close 65/8 → T41 직전 107/16, +42/+8) — T41 통합 검증 시 발견.

본 test 는 그 stale fact 를 정합화하고 향후 회귀를 차단한다.

Ceiling 갱신 규칙:
1. **부채 줄이기** (legacy fix → Phase 3 backlog): CEILING_* 도 같이 내림.
2. **새 파일 추가 with 부채**: `WI-T*-...-debt: ceiling +N` commit 별도로 갱신.
   추가 사유 commit body 에 명시. 무계획 부채 누적 차단.
3. **production lock 위반 시도** (core/cases 부채 추가): 본 test 는 tests/ 만
   감시하므로 별도 로직 불필요 — production 은 mypy --strict 직접 실행.

현재 lock 시점 (2026-05-11, T41.5 commit):
- Errors: **103**
- Affected files: **13**

이 수치는 fresh dev env 에서 ``uv run mypy --strict tests/`` 출력의
"Found N errors in M files" 라인과 일치해야 한다.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

CEILING_TOTAL_ERRORS = 103
CEILING_AFFECTED_FILES = 13

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _collect_strict_errors() -> tuple[int, set[str]]:
    """``mypy --strict tests/`` 실행 → (total_errors, {file paths})."""
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "--strict", "tests/"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    error_lines = [
        line for line in output.splitlines() if line.startswith("tests/") and ": error:" in line
    ]
    files = {line.split(":", 1)[0] for line in error_lines}
    return len(error_lines), files


def test_tests_strict_debt_does_not_grow() -> None:
    """tests/ mypy --strict 부채가 ceiling 을 넘지 않는다."""
    total, files = _collect_strict_errors()

    assert total <= CEILING_TOTAL_ERRORS, (
        f"tests/ mypy --strict 부채 회귀: {total} errors (ceiling {CEILING_TOTAL_ERRORS}). "
        f"ceiling 갱신은 별도 commit 으로 + 사유 명시. 신규 추가 file: {sorted(files)}"
    )
    assert len(files) <= CEILING_AFFECTED_FILES, (
        f"tests/ mypy --strict 영향 파일 회귀: {len(files)} files "
        f"(ceiling {CEILING_AFFECTED_FILES}). 신규 file 추가는 별도 commit + ceiling 갱신."
    )
