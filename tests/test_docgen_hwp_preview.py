"""T16: rhwp PoC 결과 + hwpx-editor Python import smoke."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from flowcoder_office_tools.docgen import hwp_preview

# hwpx-editor 스킬의 sample HWPX (Skeleton.hwpx) — import smoke에서 사용
HWPX_EDITOR_SCRIPTS = "/Users/jerome/.claude/skills/hwpx-editor/scripts"
SKELETON_HWPX = Path(
    "/Users/jerome/.claude/skills/hwpx-editor/scripts/node_modules"
    "/@ubermensch1218/hwpxcore/assets/Skeleton.hwpx"
)


# ── render_preview: PoC 실패 → NotImplementedError ─────────────────────────


def test_render_preview_raises_not_implemented(tmp_path: Path) -> None:
    """PoC 실패로 Phase 3 연기 — 호출 시 명확한 NotImplementedError."""
    fake = tmp_path / "dummy.hwpx"
    fake.write_bytes(b"not-a-real-hwpx")
    with pytest.raises(NotImplementedError) as exc:
        hwp_preview.render_preview(fake)
    msg = str(exc.value)
    # 메시지 핵심 키워드 검증 — 운영자가 fallback 경로를 즉시 알 수 있어야 함
    assert "Phase 3" in msg
    assert "hwpx-editor" in msg
    assert "rhwp-poc-decision.md" in msg


def test_render_preview_format_png_also_deferred(tmp_path: Path) -> None:
    """format=png도 동일하게 PoC 실패 메시지를 raise (format별 분기 없음 검증)."""
    fake = tmp_path / "dummy.hwpx"
    fake.write_bytes(b"x")
    with pytest.raises(NotImplementedError):
        hwp_preview.render_preview(fake, format="png")


def test_render_preview_invalid_format_raises_value_error(tmp_path: Path) -> None:
    """format 인자 검증은 NotImplementedError보다 먼저 일어나야 함 (조기 실패)."""
    fake = tmp_path / "dummy.hwpx"
    fake.write_bytes(b"x")
    with pytest.raises(ValueError, match="unknown format"):
        hwp_preview.render_preview(fake, format="svg")  # type: ignore[arg-type]


def test_rhwp_unavailable_message_actionable(tmp_path: Path) -> None:
    """R3-H1 정직성 — 메시지는 운영자가 즉시 행동 가능한 정보를 포함."""
    fake = tmp_path / "x.hwpx"
    fake.write_bytes(b"x")
    with pytest.raises(NotImplementedError) as exc:
        hwp_preview.render_preview(fake)
    msg = str(exc.value)
    # actionable 요건: (1) 어디로 갔는지, (2) 무엇으로 우회하는지, (3) 결정 출처
    assert "deferred" in msg
    assert "fallback" in msg
    assert "manually" in msg


# ── hwpx-editor Python import smoke (R3-C3 패턴) ─────────────────────────


@pytest.mark.skipif(
    not Path(HWPX_EDITOR_SCRIPTS).exists() or not SKELETON_HWPX.exists(),
    reason="hwpx-editor skill or Skeleton.hwpx sample not present in this environment",
)
def test_hwpx_editor_python_import_smoke(tmp_path: Path) -> None:
    """sys.path.insert + import 패턴이 정상 동작하는지 + analyze() 결과 검증.

    case06 (T18)은 이 패턴을 그대로 사용하므로 사전 smoke 확인이 필요.
    """
    if HWPX_EDITOR_SCRIPTS not in sys.path:
        sys.path.insert(0, HWPX_EDITOR_SCRIPTS)

    # ruff I001 disabled: lazy import은 sys.path 변경 이후에 와야 한다.
    from hwpx_utils import HwpxEditor  # type: ignore[import-untyped, import-not-found, unused-ignore]  # noqa: I001

    # Skeleton.hwpx를 tmp_path에 복사 (read-only 위치 보호)
    sample = tmp_path / "skeleton.hwpx"
    sample.write_bytes(SKELETON_HWPX.read_bytes())

    with HwpxEditor(str(sample)) as editor:
        results = editor.analyze()

    # analyze는 list[dict]를 반환 — 빈 리스트도 가능 (Skeleton.hwpx는 표가 없을 수도 있음)
    assert isinstance(results, list)
    for info in results:
        assert "index" in info
        assert "id" in info
        assert "rows" in info
        assert "cols" in info
