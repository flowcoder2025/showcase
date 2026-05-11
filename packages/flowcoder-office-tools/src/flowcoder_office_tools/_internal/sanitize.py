"""Recursive secret masking for ScenarioResult serialization.

Used by ``flowcoder_office_tools.protocols.{serialize_result, as_display}``. Kept
in ``_internal/`` so that ``dir(flowcoder_office_tools.protocols)`` does not
expose a module-level underscore helper (R1-C3, T45).
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

from flowcoder_office_tools.common.secrets_mask import mask_text

_MAX_DEPTH = 50


def _mask_recursive(value: Any, depth: int = 0) -> Any:
    if depth > _MAX_DEPTH:
        return "<TRUNCATED:depth>"
    if isinstance(value, str):
        return mask_text(value)
    if isinstance(value, bytes):
        return f"<bytes:{len(value)}>"
    if isinstance(value, dict):
        return {k: _mask_recursive(v, depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_mask_recursive(v, depth + 1) for v in value]
    if isinstance(value, Path):
        return mask_text(str(value))
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _mask_recursive(dataclasses.asdict(value), depth + 1)
    return value
