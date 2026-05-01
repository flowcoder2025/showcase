"""Jinja2 wrapper — docgen에서 견적서/메일 본문 등 템플릿 렌더링."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import jinja2

_env = jinja2.Environment(
    loader=jinja2.BaseLoader(),
    autoescape=False,  # docgen은 plain text / docx context
    keep_trailing_newline=True,
    undefined=jinja2.StrictUndefined,  # 누락 변수 즉시 raise
)


def render_string(template_str: str, context: dict[str, Any]) -> str:
    """문자열 템플릿 → 렌더링 결과."""
    return _env.from_string(template_str).render(**context)


def render_file(template_path: Path | str, context: dict[str, Any]) -> str:
    """파일 템플릿 → 렌더링 결과 (UTF-8 명시)."""
    text = Path(template_path).read_text(encoding="utf-8")
    return render_string(text, context)
