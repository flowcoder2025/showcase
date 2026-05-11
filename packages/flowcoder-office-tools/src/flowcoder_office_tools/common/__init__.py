"""Shared utility surface — config, logging, safe-mode, secret masking, timers.

Public sub-modules:
    - ``config``        : :func:`repo_root`, :func:`load`
    - ``demo_logger``   : :func:`demo_logger`, :class:`DemoLogger`, ``Logger``
    - ``safe_mode``     : :func:`is_safe`, :func:`force_safe`,
      :func:`intercept`, :func:`cache_path`, :func:`save_cache`
    - ``safe_mode_v2``  : :func:`is_safe`, :func:`force_safe`,
      :func:`safe_mode_scope`
    - ``secrets_mask``  : :func:`mask`, :func:`mask_text`
    - ``timer``         : :func:`measure`
"""

from flowcoder_office_tools.common import (
    config,
    demo_logger,
    safe_mode,
    safe_mode_v2,
    secrets_mask,
    timer,
)

__all__ = [
    "config",
    "demo_logger",
    "safe_mode",
    "safe_mode_v2",
    "secrets_mask",
    "timer",
]
