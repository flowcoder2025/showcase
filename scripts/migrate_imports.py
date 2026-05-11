"""T43 codemod — `core.X` + `cases._protocols` → `flowcoder_office_tools.X`.

ImportFrom + Import + SimpleString 3 visitor 로 다음 변환을 수행한다.

Mappings (longest prefix first):
  cases._protocols      → flowcoder_office_tools.protocols
  core                  → flowcoder_office_tools
  core.X                → flowcoder_office_tools.X

Plan v2.1.1 T43 Step 2 spec 베이스 + deviation:
  - cases._protocols 매핑 추가 (plan code는 core prefix만 처리, 33건 누락)
  - SimpleString 변환은 prefix가 dot 으로 끝나는 dotted name 만 (단독 "core" 변환 위험 차단)
  - --dry-run / --verbose 플래그 + 파일별 변환 카운트 출력

Run:
  uv run python scripts/migrate_imports.py --dry-run     # preview only
  uv run python scripts/migrate_imports.py               # apply
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable
from pathlib import Path

import libcst as cst
from libcst.codemod import CodemodContext, VisitorBasedCodemodCommand

MAPPINGS: tuple[tuple[str, str], ...] = (
    ("cases._protocols", "flowcoder_office_tools.protocols"),
    ("core", "flowcoder_office_tools"),
)

SKIP_DIR_PARTS = frozenset({".venv", "__pycache__", ".git", "node_modules", "dist", "build"})

SKIP_PATH_SUBSTRINGS = ("/scripts/migrate_imports.py",)


def _replace_dotted(text: str) -> str | None:
    """dotted-name text 에 대해 매핑 적용. 변환 없으면 None."""
    for src, dst in MAPPINGS:
        if text == src:
            return dst
        if text.startswith(src + "."):
            return dst + text[len(src) :]
    return None


def _replace_in_string_literal(inner: str) -> str | None:
    """SimpleString 내부 (quote 제외) 텍스트 변환.

    dot 으로 시작하는 dotted name 만 (예: ``core.docgen.pdf.subprocess.run``).
    단독 ``"core"`` 는 변환 안 함 (문자열 비교 등 다른 의미 가능성 차단).
    """
    for src, dst in MAPPINGS:
        if inner.startswith(src + "."):
            return dst + inner[len(src) :]
        if inner == src and src == "cases._protocols":
            return dst
    return None


class CoreToFotCommand(VisitorBasedCodemodCommand):
    DESCRIPTION = "core.X + cases._protocols → flowcoder_office_tools.X codemod"

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.import_from_count = 0
        self.import_count = 0
        self.string_count = 0

    @staticmethod
    def _module_text(node: cst.BaseExpression) -> str:
        return cst.Module([]).code_for_node(node)

    def leave_ImportFrom(
        self,
        original_node: cst.ImportFrom,
        updated_node: cst.ImportFrom,
    ) -> cst.ImportFrom:
        module = updated_node.module
        if module is None:
            return updated_node
        text = self._module_text(module)
        new_text = _replace_dotted(text)
        if new_text is None:
            return updated_node
        new_expr = cst.parse_expression(new_text)
        if not isinstance(new_expr, cst.Name | cst.Attribute):
            return updated_node
        self.import_from_count += 1
        return updated_node.with_changes(module=new_expr)

    def leave_Import(
        self,
        original_node: cst.Import,
        updated_node: cst.Import,
    ) -> cst.Import:
        new_names: list[cst.ImportAlias] = []
        changed = False
        for alias in updated_node.names:
            text = self._module_text(alias.name)
            new_text = _replace_dotted(text)
            if new_text is None:
                new_names.append(alias)
                continue
            new_expr = cst.parse_expression(new_text)
            if not isinstance(new_expr, cst.Name | cst.Attribute):
                new_names.append(alias)
                continue
            new_names.append(alias.with_changes(name=new_expr))
            changed = True
        if not changed:
            return updated_node
        self.import_count += 1
        return updated_node.with_changes(names=new_names)

    def leave_SimpleString(
        self,
        original_node: cst.SimpleString,
        updated_node: cst.SimpleString,
    ) -> cst.SimpleString:
        raw = updated_node.value
        for quote in ('"""', "'''", '"', "'"):
            if raw.startswith(quote) and raw.endswith(quote) and len(raw) >= 2 * len(quote):
                inner = raw[len(quote) : len(raw) - len(quote)]
                # multi-line / docstring 은 보통 triple-quoted + 줄바꿈 포함 → skip
                if "\n" in inner:
                    return updated_node
                new_inner = _replace_in_string_literal(inner)
                if new_inner is None:
                    return updated_node
                self.string_count += 1
                return updated_node.with_changes(value=f"{quote}{new_inner}{quote}")
        return updated_node


def _iter_targets(root: Path) -> Iterable[Path]:
    for path in root.rglob("*.py"):
        parts = set(path.parts)
        if parts & SKIP_DIR_PARTS:
            continue
        path_str = str(path)
        if any(sub in path_str for sub in SKIP_PATH_SUBSTRINGS):
            continue
        yield path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="preview without writing")
    parser.add_argument("--verbose", "-v", action="store_true", help="per-file detail")
    parser.add_argument("--root", default=".", help="search root (default: cwd)")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    total_files = 0
    total_changed = 0
    total_imp_from = 0
    total_imp = 0
    total_str = 0
    failures: list[tuple[Path, str]] = []

    for path in sorted(_iter_targets(root)):
        total_files += 1
        src = path.read_text(encoding="utf-8")
        if "core" not in src and "cases._protocols" not in src:
            continue
        try:
            module = cst.parse_module(src)
        except Exception as exc:  # noqa: BLE001
            failures.append((path, str(exc)))
            continue
        command = CoreToFotCommand(CodemodContext())
        new_module = command.transform_module(module)
        if new_module.code == src:
            continue
        total_changed += 1
        total_imp_from += command.import_from_count
        total_imp += command.import_count
        total_str += command.string_count
        if args.verbose or args.dry_run:
            rel = path.relative_to(root)
            print(
                f"[{'dry-run' if args.dry_run else 'apply'}] {rel} "
                f"ImportFrom={command.import_from_count} "
                f"Import={command.import_count} "
                f"String={command.string_count}"
            )
        if not args.dry_run:
            path.write_text(new_module.code, encoding="utf-8")

    print("---")
    print(f"scanned : {total_files} .py files under {root}")
    print(f"changed : {total_changed} files")
    print(f"  ImportFrom transforms : {total_imp_from}")
    print(f"  Import     transforms : {total_imp}")
    print(f"  String     transforms : {total_str}")
    if failures:
        print(f"failures: {len(failures)} (parse errors)")
        for path, err in failures:
            print(f"  - {path}: {err}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
