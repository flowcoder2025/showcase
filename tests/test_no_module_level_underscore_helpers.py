"""Phase 3-Pkg T45 — Block module-level underscore helpers at sub-package surface.

Each public sub-package (``flowcoder_office_tools.{excel,messaging,docgen,ocr,
ai,common,backends,protocols}``) must not expose a callable defined inside
itself with an ``_``-prefixed name. Such helpers belong under
``flowcoder_office_tools._internal/``; sub-module-deep helpers (e.g.
``ai.client._call``) are fine because they live in a non-public sub-module.

Allows:
    - dunder names (``__init__``, ``__doc__``, etc.)
    - underscore-prefixed sub-modules (``ocr._mlx_server``) — module objects,
      not callables.
    - underscore-prefixed callables that originate in a different module
      (typically because they were re-exported from ``_internal``).
"""

from __future__ import annotations

import inspect
from importlib import import_module

from tests.test_public_api_surface import PUBLIC_MODULES


def test_no_module_level_underscore_helpers() -> None:
    for mod_name in PUBLIC_MODULES:
        mod = import_module(mod_name)
        for attr_name in dir(mod):
            if attr_name.startswith("__"):
                continue
            if not attr_name.startswith("_"):
                continue
            obj = getattr(mod, attr_name)
            if not callable(obj):
                continue
            if inspect.isclass(obj):
                continue
            obj_module = getattr(obj, "__module__", None)
            assert obj_module != mod_name, (
                f"{mod_name}.{attr_name} is a module-level underscore helper. "
                "Move it under flowcoder_office_tools._internal/ and re-import. (R1-C3)"
            )
