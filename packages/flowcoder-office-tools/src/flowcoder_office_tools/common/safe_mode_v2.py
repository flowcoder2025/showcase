"""Context-local safe-mode flag (T37 Phase 3-A).

Replaces `os.environ["DEMO_SAFE"]` mutation with a ``ContextVar`` (R1-H3).
`force_safe()` returns a Token so callers can scope the override (R2-M3); the
T37 shim in ``core.common.safe_mode`` delegates here while existing callers
discard the token (their reach stays at the current Python context).

Sentinel pattern: ``_SAFE_VAR`` defaults to ``None`` meaning "not explicitly
set". ``is_safe()`` falls back to ``os.getenv("DEMO_SAFE")`` in that case so
existing env-based tests continue to work without rewrite.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token

_SAFE_VAR: ContextVar[bool | None] = ContextVar("safe_mode_v2", default=None)


def is_safe() -> bool:
    """Return True iff safe-mode is active in the current context.

    Resolution order:
        1. ``_SAFE_VAR`` if explicitly set (via ``safe_mode_scope`` / ``force_safe``).
        2. Fallback to ``os.getenv("DEMO_SAFE", "0") == "1"``.
    """
    val = _SAFE_VAR.get()
    if val is None:
        return os.getenv("DEMO_SAFE", "0") == "1"
    return val


@contextmanager
def safe_mode_scope(enabled: bool = True) -> Iterator[None]:
    """Context-managed override — auto reset on exit (LIFO with nested scopes)."""
    token = _SAFE_VAR.set(enabled)
    try:
        yield
    finally:
        _SAFE_VAR.reset(token)


def force_safe() -> Token[bool | None]:
    """Force safe-mode True; returns Token for caller-controlled reset (R2-M3).

    Existing callers (``core/ocr/gemma.py``, ``core/ai/client.py``,
    ``core/messaging/email.py``) discard the token and rely on context lifetime
    for the override to clear. T38 will migrate scenario-level callers to scope
    the override explicitly via ``with safe_mode_scope(True): ...``.
    """
    return _SAFE_VAR.set(True)
