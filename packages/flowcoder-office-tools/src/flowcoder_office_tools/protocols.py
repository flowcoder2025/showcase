"""Phase 3-A T35 — Scenario protocol surface.

Defines the typed contract between `cases.<id>.scenario.run()`, `runner.py`, and
the future `web/app.py` (Streamlit). T43 will move this module to
`packages/flowcoder-office-tools/src/flowcoder_office_tools/protocols.py`; the
existing `cases/` import path is preserved via a shim during T44.

Surface:
    - ScenarioResult — TypedDict with 6 fields each scenario must populate.
    - Backends — frozen dataclass injecting OCR/AI/Messaging implementations.
    - {OCR,AI,Messaging}Backend — runtime-checkable Protocols.
    - serialize_result(r) — disk-safe JSON dict (run.json), all secrets masked.
    - as_display(r) — Streamlit-safe dict; same sanitize as serialize_result.
      R1-C1 single sanitizer entry point: never pass raw `result` to st.* widgets.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, TypedDict, runtime_checkable

from flowcoder_office_tools._internal.sanitize import _mask_recursive

__all__ = [
    "AIBackend",
    "Backends",
    "MessagingBackend",
    "OCRBackend",
    "ScenarioResult",
    "as_display",
    "serialize_result",
]


class ScenarioResult(TypedDict):
    case_id: str
    summary_text: str
    output_files: list[Path]
    metrics: dict[str, Any]
    failures: list[dict[str, Any]]
    extras: dict[str, Any]


@runtime_checkable
class OCRBackend(Protocol):
    def extract(
        self,
        image_path: Path | str,
        *,
        model: str,
        schema: dict[str, Any] | None = None,
        prompt: str | None = None,
    ) -> dict[str, Any]: ...


@runtime_checkable
class AIBackend(Protocol):
    def chat(self, messages: list[dict[str, str]], *, model: str | None = None) -> str: ...


@runtime_checkable
class MessagingBackend(Protocol):
    def send_discord(self, content: str, *, level: str) -> None: ...
    def send_email(self, message: Any) -> None: ...


@dataclass(frozen=True)
class Backends:
    ocr: OCRBackend
    ai: AIBackend
    msg: MessagingBackend


def serialize_result(r: ScenarioResult) -> dict[str, Any]:
    """Disk JSON form (run.json). All strings/paths/nested values pass through
    secrets_mask via `_mask_recursive`."""
    return {
        "case_id": r["case_id"],
        "summary_text": _mask_recursive(r["summary_text"]),
        "output_files": [_mask_recursive(str(p)) for p in r["output_files"]],
        "metrics": _mask_recursive(r["metrics"]),
        "failures": _mask_recursive(r["failures"]),
        "extras": _mask_recursive(r["extras"]),
    }


def as_display(r: ScenarioResult) -> dict[str, Any]:
    """Streamlit display form — same sanitize as `serialize_result` (R1-C1).

    Single sanitizer entry point: every Streamlit widget must consume the dict
    returned by this function. Passing the raw `result` to `st.dataframe` /
    `st.json` / `st.markdown` is forbidden.
    """
    return serialize_result(r)
