"""Tests for core.docgen.template — Jinja2 wrapper.

T3 강한 검증 7건 (R3-H2 — trivial 통과 회피).
"""

from __future__ import annotations

from pathlib import Path

import jinja2
import pytest

from core.docgen import template


def test_render_string_substitutes_basic_vars() -> None:
    result = template.render_string(
        "안녕 {{ name }}, {{ amount }}원",
        {"name": "박과장", "amount": 1500000},
    )
    assert result == "안녕 박과장, 1500000원"


def test_render_string_strict_undefined_raises() -> None:
    with pytest.raises(jinja2.UndefinedError):
        template.render_string("Hello {{ missing }}", {})


def test_render_file_utf8_preserved(tmp_path: Path) -> None:
    tmpl_path = tmp_path / "tmpl.txt"
    tmpl_path.write_text("{{ title }}: {{ vendor }}", encoding="utf-8")
    result = template.render_file(
        tmpl_path,
        {"title": "거래명세서", "vendor": "AX상사"},
    )
    assert result == "거래명세서: AX상사"


def test_render_file_path_str_or_pathlib(tmp_path: Path) -> None:
    tmpl_path = tmp_path / "tmpl.txt"
    tmpl_path.write_text("hello {{ who }}", encoding="utf-8")
    result_path = template.render_file(tmpl_path, {"who": "world"})
    result_str = template.render_file(str(tmpl_path), {"who": "world"})
    assert result_path == "hello world"
    assert result_str == "hello world"


def test_render_string_keeps_trailing_newline() -> None:
    result = template.render_string("line1\nline2\n", {})
    assert result.endswith("\n")
    assert result == "line1\nline2\n"


def test_render_string_no_autoescape() -> None:
    result = template.render_string(
        "<b>{{ x }}</b>",
        {"x": "<script>"},
    )
    assert result == "<b><script></b>"
    assert "&lt;" not in result


def test_render_file_missing_file_raises(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.txt"
    with pytest.raises(FileNotFoundError):
        template.render_file(missing, {})
