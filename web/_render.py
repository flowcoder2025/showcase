"""Phase 3-Web T49 — single sanitizer boundary for Streamlit result rendering.

Every widget call (``st.success`` / ``st.dataframe`` / ``st.warning`` /
``st.json``) consumes the dict returned by :func:`as_display`. Passing a raw
``ScenarioResult`` directly to a widget is forbidden (R1-C1) — masking is
applied recursively for every string, ``Path``, dict and list value.

``output_files`` is the one case where the underlying ``Path`` *must* be read
from disk to populate ``st.download_button``. We pair each raw path with its
sanitized string by position (``zip(..., strict=True)``) so the display label,
the file name shown to the browser and the widget key all use the masked form,
while only the bytes from disk flow through unmodified.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import streamlit as st
from flowcoder_office_tools.common.secrets_mask import mask_text
from flowcoder_office_tools.protocols import ScenarioResult, as_display


def render_result(result: Mapping[str, Any]) -> None:
    """Render a completed run via the single ``as_display()`` sanitizer (R1-C1)."""
    raw = cast(ScenarioResult, result["result"])
    safe = as_display(raw)

    summary = safe["summary_text"]
    if summary:
        st.success(summary)

    raw_files: list[Path] = list(raw["output_files"])
    safe_files: list[str] = list(safe["output_files"])
    if raw_files:
        st.subheader("생성 파일")
        for raw_path, safe_path in zip(raw_files, safe_files, strict=True):
            p = Path(raw_path)
            if not p.exists():
                st.caption(f"(누락) {safe_path}")
                continue
            safe_name = mask_text(p.name)
            with p.open("rb") as fh:
                st.download_button(
                    label=f"⬇ {safe_name}",
                    data=fh.read(),
                    file_name=safe_name,
                    key=f"dl_{safe_path}",
                )

    if safe["metrics"]:
        st.subheader("메트릭")
        st.dataframe(safe["metrics"])

    if safe["failures"]:
        st.subheader("실패")
        st.warning(f"{len(safe['failures'])}건 실패")
        st.dataframe(safe["failures"])

    if safe["extras"]:
        with st.expander("추가 정보", expanded=False):
            st.json(safe["extras"])
