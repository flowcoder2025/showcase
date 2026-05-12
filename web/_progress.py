"""Phase 3-Web T49 — Streamlit progress adapter for ``ProgressEvent`` stream.

CLI uses ``rich_progress_adapter`` (T40). Streamlit reuses the same fire-and-
forget contract (R2-H3) but renders into a ``st.progress`` bar bound to a
``DeltaGenerator`` placeholder so the bar can sit anywhere on the page.

Wiring through ``execute_case`` is intentionally deferred to a later task —
T49 delivers the adapter as a module so smoke tests can import it and a future
patch can plumb it through without touching the public surface again.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from flowcoder_office_tools.progress import ProgressEvent

if TYPE_CHECKING:
    from streamlit.delta_generator import DeltaGenerator


def streamlit_progress_adapter(
    placeholder: DeltaGenerator,
) -> Callable[[ProgressEvent], None]:
    """Return a ``ProgressEvent`` callback that drives a ``st.progress`` bar.

    ``ProgressEvent`` is a ``TypedDict`` (``index``/``total``/``message`` —
    *not* ``processed``/``label`` as an early draft suggested). Events without
    a numeric position (``kind == "done"`` or ``index/total is None``) leave
    the bar at its prior fill so a single ``done`` does not snap it back to 0.
    """
    bar = placeholder.progress(0, text="시작 대기 중")

    def cb(evt: ProgressEvent) -> None:
        index = evt["index"]
        total = evt["total"]
        if evt["kind"] == "done" or index is None or total is None:
            return
        pct = min(int(index * 100 / max(total, 1)), 100)
        bar.progress(
            pct,
            text=f"{evt['case_id']}: {index}/{total} — {evt['message']}",
        )

    return cb
