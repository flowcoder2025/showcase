"""Backwards-compat shim. Lazy meta path finder — eager import 0.

T43~T46 임시 shim. ``import core.X.Y`` / ``from core.X import Y`` /
``from core.X.Y import Z`` 패턴을 ``flowcoder_office_tools.X.Y`` 로 lazy forward
한다. T46 에서 제거 예정.

Architecture (T44 — plan note 보강):
- Plan v2.1.1 T44 가 "Python ModuleType ``__getattr__`` 가 import 시점에 자동 해결되므로
  명시 불필요" 라고 가정했으나 실 동작이 다름. ``from core.excel.reader import read_excel``
  같은 deep import 는 Python import 시스템이 ``core.excel`` sub-module 을 먼저
  찾는데, ``__getattr__`` 는 attribute access hook 이라 import resolution 단계에서
  호출되지 않는다 → ``ModuleNotFoundError: No module named 'core.excel'``.
- 정답: ``sys.meta_path`` 에 ``MetaPathFinder`` 등록 → ``core.*`` import 를 가로채
  대응 ``flowcoder_office_tools.*`` 모듈로 alias.

DeprecationWarning 정책:
- sub-package (top-level under core, 예: ``core.ai``) 당 1회만 emit.
- ``_warned`` set 으로 추적. ``core.ai`` 와 ``core.ai.client`` 는 같은 ``ai`` bucket.
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.machinery
import sys
import warnings
from types import ModuleType

_warned: set[str] = set()


def _ensure_warning(top: str) -> None:
    """sub-package ``top`` 에 대해 한 번만 DeprecationWarning 을 emit."""
    if top in _warned:
        return
    _warned.add(top)
    warnings.warn(
        f"Importing 'core.{top}' is deprecated; use "
        f"'flowcoder_office_tools.{top}' (T46 shim 제거 예정).",
        DeprecationWarning,
        stacklevel=4,
    )


class _CoreShimLoader(importlib.abc.Loader):
    """``core.X[...Y]`` 를 ``flowcoder_office_tools.X[...Y]`` alias 로 load."""

    def __init__(self, fullname: str) -> None:
        self._fullname = fullname

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> ModuleType:
        suffix = self._fullname[len("core.") :]
        target = f"flowcoder_office_tools.{suffix}"
        # import_module 은 cached sys.modules entry 를 반환하므로 동일 객체.
        module = importlib.import_module(target)
        sys.modules[self._fullname] = module
        return module

    def exec_module(self, module: ModuleType) -> None:
        # alias 이므로 별도 execution 불필요 (대상 모듈은 이미 import 완료).
        return None


class _CoreShimFinder(importlib.abc.MetaPathFinder):
    """``sys.meta_path`` 등록용 finder — ``core.X[...]`` import 를 가로챈다."""

    def find_spec(
        self,
        fullname: str,
        path: object,
        target: ModuleType | None = None,
    ) -> importlib.machinery.ModuleSpec | None:
        if not fullname.startswith("core."):
            return None
        # ``core.X.Y.Z`` → top sub-package 는 ``X``.
        top = fullname.split(".", 2)[1]
        _ensure_warning(top)
        return importlib.machinery.ModuleSpec(fullname, _CoreShimLoader(fullname))


def __getattr__(name: str) -> ModuleType:
    """``import core; core.X`` 같은 attribute access 도 동일 alias 로 forward."""
    if name.startswith("_"):
        raise AttributeError(name)
    _ensure_warning(name)
    target = f"flowcoder_office_tools.{name}"
    module = importlib.import_module(target)
    sys.modules[f"core.{name}"] = module
    return module


# Idempotent — 모듈 reload 시에도 finder 가 중복 등록되지 않는다.
# Insert at front of sys.meta_path: 기본 PathFinder 보다 먼저 호출되어야
# ``core.X.Y`` 의 sub-sub import 가 path-based 로 별도 module 객체로 잡히지 않는다.
if not any(isinstance(f, _CoreShimFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _CoreShimFinder())
