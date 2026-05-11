"""T18: case06 — 정부지원사업 신청서 HWPX 자동 작성 (T38 ScenarioResult)."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
import yaml
from flowcoder_office_tools.docgen import hwpx

from cases.case06_hwpx_govt_form_filler import scenario
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


def _run(template: Path, out_dir: Path, data: GrantApplication | None = None) -> dict:
    cfg = {"template_path": template}
    if data is not None:
        cfg["data"] = data
    return scenario.run(output_dir=out_dir, config=cfg)


def test_scenario_runs_safe_mode_returns_scenario_result(
    tmp_path: Path, template_present: Path
) -> None:
    result = _run(template_present, tmp_path)
    for key in ("case_id", "summary_text", "output_files", "metrics", "failures", "extras"):
        assert key in result, f"missing key: {key}"
    assert result["case_id"] == "case06"
    assert isinstance(result["output_files"], list)
    assert len(result["output_files"]) == 1
    assert isinstance(result["metrics"]["fields_filled"], int)
    assert isinstance(result["metrics"]["verification_passed"], bool)
    assert isinstance(result["metrics"]["elapsed_seconds"], float)
    assert isinstance(result["extras"]["missing_values"], list)


def test_scenario_creates_output_hwpx(tmp_path: Path, template_present: Path) -> None:
    result = _run(template_present, tmp_path)
    out_path = result["output_files"][0]
    assert out_path.exists()
    assert out_path.stat().st_size > 0
    assert zipfile.is_zipfile(out_path)


def test_scenario_fills_all_grant_fields(tmp_path: Path, template_present: Path) -> None:
    result = _run(template_present, tmp_path)
    extracted = hwpx.extract_text(result["output_files"][0])
    assert AX_TRADING_GRANT["company_name"] in extracted
    assert AX_TRADING_GRANT["ceo_name"] in extracted
    assert AX_TRADING_GRANT["biznum"] in extracted
    assert AX_TRADING_GRANT["business_area"] in extracted
    assert f"{AX_TRADING_GRANT['grant_amount']:,}원" in extracted
    assert f"{AX_TRADING_GRANT['annual_revenue']:,}원" in extracted
    assert f"{AX_TRADING_GRANT['employee_count']}명" in extracted
    assert AX_TRADING_GRANT["application_date"] in extracted


def test_scenario_verification_passes(tmp_path: Path, template_present: Path) -> None:
    result = _run(template_present, tmp_path)
    assert result["metrics"]["verification_passed"] is True
    assert result["extras"]["missing_values"] == []
    assert result["metrics"]["fields_filled"] == 8


def test_scenario_idempotent(tmp_path: Path, template_present: Path) -> None:
    r1 = _run(template_present, tmp_path)
    r2 = _run(template_present, tmp_path)
    assert r1["output_files"][0] == r2["output_files"][0]
    out_path = r2["output_files"][0]
    assert zipfile.is_zipfile(out_path)
    text = hwpx.extract_text(out_path)
    assert AX_TRADING_GRANT["company_name"] in text
    assert r2["metrics"]["verification_passed"] is True


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


def test_scenario_missing_template_raises(tmp_path: Path) -> None:
    missing = tmp_path / "nope.hwpx"
    with pytest.raises(FileNotFoundError):
        _run(missing, tmp_path)


def test_scenario_empty_field_raises_value_error(tmp_path: Path, template_present: Path) -> None:
    bad: GrantApplication = dict(AX_TRADING_GRANT)  # type: ignore[assignment]
    bad["company_name"] = "   "
    with pytest.raises(ValueError, match="empty/blank"):
        _run(template_present, tmp_path, data=bad)
