"""Phase 3-Pkg T45 — Public API surface lock.

Each sub-package's ``__all__`` defines the supported import surface; this test
captures a signature snapshot and fails when symbols are added, removed, or
re-typed without an explicit ``snapshot/public_api.json`` update.

Surface change procedure:
1. Make the source change behind a deliberate decision.
2. Re-run with ``UPDATE_SNAPSHOT=1`` to rewrite ``snapshots/public_api.json``.
3. Commit the snapshot delta together with the source change and document the
   reason in the PR description (``BREAKING CHANGE:`` prefix when removing or
   re-typing a public symbol).
"""

from __future__ import annotations

import dataclasses
import inspect
import json
import os
import types
from importlib import import_module
from pathlib import Path
from typing import Any, get_type_hints

PUBLIC_MODULES: tuple[str, ...] = (
    "flowcoder_office_tools.excel",
    "flowcoder_office_tools.messaging",
    "flowcoder_office_tools.docgen",
    "flowcoder_office_tools.ocr",
    "flowcoder_office_tools.ai",
    "flowcoder_office_tools.common",
    "flowcoder_office_tools.backends",
    "flowcoder_office_tools.protocols",
)

SNAPSHOT_PATH = Path(__file__).parent / "snapshots" / "public_api.json"


def _surface_repr(obj: Any) -> str:
    """callable이면 signature, dataclass/TypedDict면 fields, module이면 name."""
    if isinstance(obj, types.ModuleType):
        return f"module({obj.__name__})"
    try:
        return f"sig:{inspect.signature(obj)}"
    except (TypeError, ValueError):
        pass
    if dataclasses.is_dataclass(obj):
        fields = sorted(f.name for f in dataclasses.fields(obj))
        return f"dataclass({fields})"
    try:
        hints = get_type_hints(obj)
        if hints:
            return f"TypedDict({sorted(hints.keys())})"
    except Exception:
        pass
    return f"<{type(obj).__name__}>"


def _capture_surface() -> dict[str, dict[str, str]]:
    surface: dict[str, dict[str, str]] = {}
    for mod_name in PUBLIC_MODULES:
        mod = import_module(mod_name)
        all_list = getattr(mod, "__all__", None)
        assert all_list is not None, f"{mod_name} missing __all__"
        for name in all_list:
            assert not name.startswith("_"), (
                f"{mod_name}.{name} starts with underscore — exclude from __all__"
            )
        surface[mod_name] = {name: _surface_repr(getattr(mod, name)) for name in all_list}
    return surface


def test_public_api_matches_snapshot() -> None:
    actual = _capture_surface()

    if os.environ.get("UPDATE_SNAPSHOT") == "1":
        SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_PATH.write_text(
            json.dumps(actual, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return

    assert SNAPSHOT_PATH.exists(), (
        f"Snapshot missing: {SNAPSHOT_PATH}. "
        "Generate baseline once with UPDATE_SNAPSHOT=1 pytest ..."
    )
    expected = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    if actual != expected:
        diff_payload = json.dumps({"expected": expected, "actual": actual}, indent=2)
        raise AssertionError(
            "Public API surface changed. If intentional, document the reason in "
            "the PR description (use 'BREAKING CHANGE:' prefix for removals or "
            "re-typed symbols) and regenerate the snapshot:\n"
            "    UPDATE_SNAPSHOT=1 uv run pytest tests/test_public_api_surface.py\n"
            f"\nDiff:\n{diff_payload}"
        )


def test_no_underscore_in_all() -> None:
    for mod_name in PUBLIC_MODULES:
        mod = import_module(mod_name)
        for name in getattr(mod, "__all__", []):
            assert not name.startswith("_"), f"{mod_name}.{name} 차단"
