"""Backwards-compat shim. Lazy ``__getattr__`` — eager import 0.

T43~T46 임시 shim. ``import core.X`` / ``from core import X`` / ``from core.X import Y``
패턴을 ``flowcoder_office_tools.X`` 로 lazy forward 한다. T46 에서 제거 예정.
"""

from __future__ import annotations

import sys
import warnings
from importlib import import_module
from types import ModuleType

_warned: set[str] = set()


def __getattr__(name: str) -> ModuleType:
    if name.startswith("_"):
        raise AttributeError(name)
    if name not in _warned:
        warnings.warn(
            f"Importing 'core.{name}' is deprecated; use "
            f"'flowcoder_office_tools.{name}' (T46 shim 제거 예정).",
            DeprecationWarning,
            stacklevel=2,
        )
        _warned.add(name)
    target = f"flowcoder_office_tools.{name}"
    module = import_module(target)
    sys.modules[f"core.{name}"] = module
    return module
