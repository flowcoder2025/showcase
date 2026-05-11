"""T44 — `core/` shim deep-import 호환 검증.

T43 이주 후 `core/__init__.py` 는 lazy `__getattr__` 로 `flowcoder_office_tools.X`
로 forward 하는 shim 이다. 외부 consumer 가 `from core.X.Y import Z` 같은 deep
import 패턴을 그대로 사용해도 동일 객체에 도달해야 한다.

검증 항목 (plan v2.1.1 T44 AC):
1. deep import (sub.sub) — `from core.excel.reader import read_excel` 등 동작
2. 양쪽 import 가 ``is`` 비교 통과 (sys.modules 동일 entry 사용)
3. DeprecationWarning 이 같은 sub-module 당 1회만 (`_warned` 셋 보장)
4. cases._protocols → flowcoder_office_tools.protocols 이름 변경 후 shim 경로
   ``from core.protocols import X`` 동작 (cases 가 아닌 core 네임스페이스 경유)
"""

from __future__ import annotations

import importlib
import sys
import warnings


def test_deep_import_via_shim_excel_reader() -> None:
    """``from core.excel.reader import read_dir`` deep import 동작 + 객체 동일성.

    plan v2.1.1 T44 spec 예시는 ``read_excel`` 이었지만 실 라이브러리는 ``read_dir`` 만
    export — plan code deviation. 검증 의도 (deep sub-sub import alias) 는 동일.
    """
    # 이전 테스트가 sys.modules 에 등록한 entry 가 있으면 isolated 검증 어려움 → 사전 제거.
    for key in [k for k in sys.modules if k.startswith("core.")]:
        del sys.modules[key]

    from core.excel.reader import read_dir as core_read  # type: ignore[import-not-found]
    from flowcoder_office_tools.excel.reader import read_dir as fot_read

    assert core_read is fot_read


def test_deep_import_via_shim_messaging_email() -> None:
    """messaging.email 도 동일 패턴 — sub-package + sub-module."""
    for key in [k for k in sys.modules if k.startswith("core.")]:
        del sys.modules[key]

    from core.messaging.email import build_html_body as core_build  # type: ignore[import-not-found]
    from flowcoder_office_tools.messaging.email import build_html_body as fot_build

    assert core_build is fot_build


def test_protocols_via_shim() -> None:
    """`cases._protocols` → `flowcoder_office_tools.protocols` 이름변경 후 shim 경로 검증."""
    for key in [k for k in sys.modules if k.startswith("core.")]:
        del sys.modules[key]

    from core.protocols import ScenarioResult as core_proto  # type: ignore[import-not-found]
    from flowcoder_office_tools.protocols import ScenarioResult as fot_proto

    assert core_proto is fot_proto


def test_shim_emits_deprecation_warning_once_per_submodule() -> None:
    """동일 sub-module 을 여러 번 import 해도 DeprecationWarning 은 첫 호출 1회."""
    # warned 캐시 + sys.modules 청소 — fresh state.
    import core as _core_pkg

    _core_pkg._warned.clear()
    for key in [k for k in sys.modules if k.startswith("core.")]:
        del sys.modules[key]

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        # 첫 호출 — warn 발생
        importlib.import_module("core.excel")
        # 두 번째 호출 — warn 추가로 발생하면 안 됨 (_warned 캐시)
        importlib.import_module("core.excel")

    excel_warnings = [
        w
        for w in caught
        if issubclass(w.category, DeprecationWarning) and "core.excel" in str(w.message)
    ]
    assert len(excel_warnings) == 1, (
        f"expected 1 DeprecationWarning for 'core.excel', got {len(excel_warnings)}"
    )


def test_shim_warning_distinct_for_different_submodules() -> None:
    """다른 sub-module 은 각자 1회씩 warn — `_warned` 가 sub-module 별 카운트."""
    import core as _core_pkg

    _core_pkg._warned.clear()
    for key in [k for k in sys.modules if k.startswith("core.")]:
        del sys.modules[key]

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        importlib.import_module("core.ai")
        importlib.import_module("core.common")
        importlib.import_module("core.ai")  # 2회째 — warn 없음

    ai_warnings = [
        w
        for w in caught
        if issubclass(w.category, DeprecationWarning) and "core.ai" in str(w.message)
    ]
    common_warnings = [
        w
        for w in caught
        if issubclass(w.category, DeprecationWarning) and "core.common" in str(w.message)
    ]
    assert len(ai_warnings) == 1
    assert len(common_warnings) == 1
