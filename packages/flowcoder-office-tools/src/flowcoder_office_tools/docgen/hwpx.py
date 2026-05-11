"""HWPX 양식 자동 채우기 — hwpx-editor 스킬 래퍼.

case06 (정부지원사업 신청서 자동화) 시연에서 호출하는 thin wrapper. 실제
편집 로직은 외부 스킬(`hwpx-editor`)의 ``HwpxEditor`` 클래스가 담당하며,
본 모듈은 다음 책임만 진다:

1. 스킬 디렉토리를 ``sys.path``에 추가해 ``hwpx_utils`` 모듈을 import한다
   (R3-C3 패턴). 환경변수 ``AX_HWPX_EDITOR_DIR``로 위치 override 가능.
2. ``HwpxEditor`` 호출 중 발생하는 모든 예외를 ``ValueError``로 통일하고
   ``__cause__`` 체인을 보존한다 (caller 친화성).
3. 결과 .hwpx에서 텍스트를 추출하는 ``extract_text``를 제공해 시나리오/
   테스트가 채워진 값을 검증할 수 있게 한다.

Module-call convention: ``from core.docgen import hwpx; hwpx.fill_form(...)``.
직접 함수 import 금지 — safe_mode patch boundary와 일관성 유지.

빈 ``cell_fills``/``text_replacements`` 호출 시에도 출력 파일이 생성되어야
하므로 ``HwpxEditor`` 호출 자체는 항상 수행한다 (open → save 패스스루).
이렇게 하면 ``linesegarray`` 캐시 제거가 일관되게 일어나 한글에서 열 때
레이아웃 깨짐이 방지된다.
"""

from __future__ import annotations

import os
import sys
import zipfile
from pathlib import Path
from typing import Any

from lxml import etree

# hwpx-editor 스킬 위치 — 환경변수로 override 가능 (CI/타 사용자 환경 호환)
_HWPX_SKILL_DIR = os.environ.get(
    "AX_HWPX_EDITOR_DIR",
    "/Users/jerome/.claude/skills/hwpx-editor/scripts",
)


def _import_hwpx_editor() -> Any:
    """``HwpxEditor`` 클래스를 lazy import.

    매 호출마다 ``sys.path`` 상태를 확인해 ``_HWPX_SKILL_DIR``이 빠져 있으면
    추가한다. 환경변수가 잘못된 경로를 가리키면 ``ImportError``가 자연스럽게
    전파되도록 한다 (caller가 진단 가능).
    """
    if _HWPX_SKILL_DIR not in sys.path:
        sys.path.insert(0, _HWPX_SKILL_DIR)
    # ruff I001 disabled: 이 import은 sys.path 변경 이후에 와야 한다 (lazy 의도).
    from hwpx_utils import HwpxEditor  # type: ignore[import-untyped, import-not-found, unused-ignore]  # noqa: I001

    return HwpxEditor


def fill_form(
    *,
    template_path: Path | str,
    out_path: Path | str,
    cell_fills: list[dict[str, Any]] | None = None,
    text_replacements: list[dict[str, Any]] | None = None,
) -> None:
    """HWPX 템플릿을 열어 셀 채우기/텍스트 치환 후 새 파일로 저장.

    Args:
        template_path: 입력 .hwpx 경로 (없으면 ``FileNotFoundError``)
        out_path: 출력 .hwpx 경로 (부모 디렉토리는 자동 생성)
        cell_fills: ``[{"table_id": str, "col": int, "row": int, "text": str,
            "label": str (optional)}, ...]`` — 각 항목은 ``HwpxEditor.set_cell``
            kwargs로 그대로 전달. ``None`` 또는 빈 리스트면 셀 채우기 없이
            템플릿 패스스루 (linesegarray만 정리).
        text_replacements: ``[{"table_id": str, "col": int, "row": int,
            "old": str, "new": str, "label": str (optional)}, ...]``
            (값 타입은 의미상 mixed이므로 ``dict[str, Any]``로 받음) —
            ``HwpxEditor.replace_in_cell`` kwargs로 전달. 체크박스 토글
            (``"□ X"`` → ``"☑ X"``)에 사용.

    Raises:
        FileNotFoundError: ``template_path``가 존재하지 않을 때
        ValueError: ``HwpxEditor`` 호출 중 발생한 모든 예외 (zip 손상,
            section0.xml 누락, table_id mismatch 등)를 wrap하여 raise.
            ``__cause__``로 원본 예외를 노출.
    """
    tpl = Path(template_path)
    if not tpl.exists():
        raise FileNotFoundError(f"HWPX template not found: {tpl}")

    cell_fills = cell_fills or []
    text_replacements = text_replacements or []

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    HwpxEditor = _import_hwpx_editor()

    try:
        with HwpxEditor(str(tpl)) as editor:
            for fill in cell_fills:
                kwargs = dict(fill)
                editor.set_cell(**kwargs)
            for repl in text_replacements:
                kwargs = dict(repl)
                editor.replace_in_cell(**kwargs)
            editor.save(str(out))
    except FileNotFoundError:
        # HwpxEditor 내부에서 raise한 FileNotFoundError (e.g. section0.xml 누락)는
        # 원본 ``template_path`` 부재와 구분이 안 되므로 ValueError로 wrap.
        raise
    except (zipfile.BadZipFile, etree.XMLSyntaxError) as e:
        raise ValueError(f"corrupt HWPX template: {tpl} ({e})") from e
    except (KeyError, AttributeError, ValueError, TypeError) as e:
        raise ValueError(f"HwpxEditor failed on {tpl}: {e}") from e


def extract_text(hwpx_path: Path | str) -> str:
    """HWPX 파일에서 모든 텍스트를 추출 (검증·검색용).

    내부 구현은 ZIP에서 ``.xml`` 엔트리를 찾아 lxml로 파싱하고
    ``itertext()``로 모든 텍스트 노드를 모은다. 빈 줄/whitespace-only는
    제거하지만 셀 간 공백·순서는 보존하지 않는다 (검증 용도이지 충실
    재현 용도가 아니므로).

    Args:
        hwpx_path: 입력 .hwpx 경로

    Returns:
        non-whitespace 텍스트들을 ``\\n``으로 join한 문자열. 텍스트가
        하나도 없으면 빈 문자열.

    Raises:
        FileNotFoundError: 파일이 없을 때
        ValueError: ZIP/XML 파싱 실패 시 (``__cause__`` 체인 보존)
    """
    hp = Path(hwpx_path)
    if not hp.exists():
        raise FileNotFoundError(f"HWPX file not found: {hp}")

    chunks: list[str] = []
    try:
        with zipfile.ZipFile(hp) as zf:
            xml_names = [n for n in zf.namelist() if n.lower().endswith(".xml")]
            for name in xml_names:
                with zf.open(name) as f:
                    try:
                        tree = etree.parse(f)
                    except etree.XMLSyntaxError:
                        # 일부 보조 .xml은 한글 비표준 — skip 해도 검증엔 무관
                        continue
                    for text in tree.getroot().itertext():
                        s = (text or "").strip()
                        if s:
                            chunks.append(s)
    except zipfile.BadZipFile as e:
        raise ValueError(f"not a valid HWPX (zip) file: {hp}") from e

    return "\n".join(chunks)
