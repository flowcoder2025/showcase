"""T18: case06 — 정부지원사업 신청서 HWPX 자동 작성.

End-to-end against the real ``grant_application_template.hwpx`` fixture
(no mocks — fixture is local hwpx-editor, no external API). Skips when the
fixture or the hwpx-editor skill is unavailable in CI.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
import yaml

from cases.case06_hwpx_govt_form_filler import scenario
from core.docgen import hwpx
from personas.sample_data.grant_data import AX_TRADING_GRANT, GrantApplication

FIXTURE = (
    Path(__file__).parent.parent
    / "personas"
    / "sample_data"
    / "forms"
    / "grant_application_template.hwpx"
)


@pytest.fixture
def template_present() -> Path:
    if not FIXTURE.exists():
        pytest.skip(
            "grant_application_template.hwpx missing — run personas/scripts/build_grant_template.py"
        )
    return FIXTURE


# ── 1. safe-mode dict shape ────────────────────────────────────────────


def test_scenario_runs_safe_mode_returns_dict(tmp_path: Path, template_present: Path) -> None:
    summary = scenario.run(template_path=template_present, output_dir=tmp_path, safe=True)
    for key in (
        "output_path",
        "fields_filled",
        "verification_passed",
        "elapsed_seconds",
        "missing_values",
    ):
        assert key in summary, f"missing key: {key}"
    assert isinstance(summary["output_path"], str)
    assert isinstance(summary["fields_filled"], int)
    assert isinstance(summary["verification_passed"], bool)
    assert isinstance(summary["elapsed_seconds"], float)
    assert isinstance(summary["missing_values"], list)


# ── 2. output exists & is a real zip ──────────────────────────────────


def test_scenario_creates_output_hwpx(tmp_path: Path, template_present: Path) -> None:
    summary = scenario.run(template_path=template_present, output_dir=tmp_path)
    out_path = Path(summary["output_path"])
    assert out_path.exists()
    assert out_path.stat().st_size > 0
    assert zipfile.is_zipfile(out_path)


# ── 3. all 8 grant fields appear in the output ────────────────────────


def test_scenario_fills_all_grant_fields(tmp_path: Path, template_present: Path) -> None:
    summary = scenario.run(template_path=template_present, output_dir=tmp_path)
    extracted = hwpx.extract_text(Path(summary["output_path"]))
    # Each expected display value must appear (with formatting helpers applied).
    assert AX_TRADING_GRANT["company_name"] in extracted
    assert AX_TRADING_GRANT["ceo_name"] in extracted
    assert AX_TRADING_GRANT["biznum"] in extracted
    assert AX_TRADING_GRANT["business_area"] in extracted
    assert f"{AX_TRADING_GRANT['grant_amount']:,}원" in extracted
    assert f"{AX_TRADING_GRANT['annual_revenue']:,}원" in extracted
    assert f"{AX_TRADING_GRANT['employee_count']}명" in extracted
    assert AX_TRADING_GRANT["application_date"] in extracted


# ── 4. verification flag flips correctly ──────────────────────────────


def test_scenario_verification_passes(tmp_path: Path, template_present: Path) -> None:
    summary = scenario.run(template_path=template_present, output_dir=tmp_path)
    assert summary["verification_passed"] is True
    assert summary["missing_values"] == []
    assert summary["fields_filled"] == 8


# ── 5. idempotent reruns ──────────────────────────────────────────────


def test_scenario_idempotent(tmp_path: Path, template_present: Path) -> None:
    s1 = scenario.run(template_path=template_present, output_dir=tmp_path)
    s2 = scenario.run(template_path=template_present, output_dir=tmp_path)
    assert s1["output_path"] == s2["output_path"]
    out_path = Path(s2["output_path"])
    # second run overwrote cleanly — still a valid zip with the values present.
    assert zipfile.is_zipfile(out_path)
    text = hwpx.extract_text(out_path)
    assert AX_TRADING_GRANT["company_name"] in text
    assert s2["verification_passed"] is True


# ── 6. meta.yaml shape ────────────────────────────────────────────────


def test_scenario_meta_yaml_loads() -> None:
    meta_path = Path("cases/case06_hwpx_govt_form_filler/meta.yaml")
    assert meta_path.exists()
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    assert meta["id"] == "case06_hwpx_govt_form_filler"
    assert meta["category"] == "docgen"
    assert meta["persona"] == "김사장"
    assert meta["external_apis"] == []
    for length in ("1min", "3min", "5min"):
        assert length in meta["demo_lengths"]


# ── 7. missing template raises FileNotFoundError ──────────────────────


def test_scenario_missing_template_raises(tmp_path: Path) -> None:
    missing = tmp_path / "nope.hwpx"
    with pytest.raises(FileNotFoundError):
        scenario.run(template_path=missing, output_dir=tmp_path)


# ── 8. empty/blank field in custom data raises ValueError ─────────────


def test_scenario_empty_field_raises_value_error(tmp_path: Path, template_present: Path) -> None:
    bad: GrantApplication = dict(AX_TRADING_GRANT)  # type: ignore[assignment]
    bad["company_name"] = "   "  # whitespace-only
    with pytest.raises(ValueError, match="empty/blank"):
        scenario.run(template_path=template_present, output_dir=tmp_path, data=bad)
