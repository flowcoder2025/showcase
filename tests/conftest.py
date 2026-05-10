"""Cross-test isolation for `core.common.safe_mode_v2._SAFE_VAR` (T37).

`force_safe()`를 사용하는 test가 token을 discard하면 ContextVar는 후속 test에
누설된다. autouse fixture로 매 test 시작/종료 시점에 sentinel(None)로 reset해
독립성을 보장한다. None은 "값 없음 — env로 fallback" 표시.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from core.common.safe_mode_v2 import _SAFE_VAR


@pytest.fixture(autouse=True)
def _safe_mode_isolation() -> Iterator[None]:
    token = _SAFE_VAR.set(None)
    try:
        yield
    finally:
        _SAFE_VAR.reset(token)
